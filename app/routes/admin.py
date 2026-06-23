import json
import os
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.decorators import role_required
from app.forms import AssignDoctorPatientForm, EducationForm, ForwardReportToDoctorsForm, ModelSelectForm, ResetPasswordForm, UserEditForm
from app.ml.pipeline import MODEL_BUILDERS, clean_data, generate_eda, load_dataset, train_all_models
from app.ml.predictor import clear_model_cache
from app.ml.retrain import retrain_with_feedback
from app.ml.validators import validate_dataset_columns
from app.ml.reports import generate_eda_pdf
from app.models import (
    AdminReportSubmission, AuditLog, Dataset, DoctorReportForward, EducationResource,
    Feedback, HealthRecord, ModelMetrics, ProviderPatient, TrainingJob, User,
)
from app.utils import (
    get_production_model_name, get_unread_admin_feedback_count, get_unread_admin_reports_count,
    log_audit, parse_admin_report_display_data, set_production_model_name,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@login_required
@role_required("admin")
def admin_dashboard():
    datasets = Dataset.query.order_by(Dataset.uploaded_at.desc()).all()
    metrics = ModelMetrics.query.order_by(ModelMetrics.f1_score.desc()).all()
    jobs = TrainingJob.query.order_by(TrainingJob.started_at.desc()).limit(5).all()
    return render_template(
        "admin/dashboard.html",
        datasets=datasets,
        metrics=metrics,
        user_count=User.query.count(),
        feedback_count=Feedback.query.count(),
        pending_feedback=Feedback.query.filter_by(used_in_training=False).filter(
            Feedback.actual_outcome.isnot(None)
        ).count(),
        assignment_count=ProviderPatient.query.count(),
        doctor_count=User.query.filter_by(role="provider", is_active=True).count(),
        patient_count=User.query.filter_by(role="patient", is_active=True).count(),
        unread_reports=get_unread_admin_reports_count(),
        unread_feedback=get_unread_admin_feedback_count(),
        jobs=jobs,
        production_model=get_production_model_name(),
    )


@admin_bp.route("/upload-dataset", methods=["GET", "POST"])
@login_required
@role_required("admin")
def upload_dataset():
    if request.method == "POST":
        file = request.files.get("dataset")
        if not file or not file.filename.lower().endswith(".csv"):
            flash("Please upload a valid CSV file.", "danger")
            return redirect(url_for("admin.upload_dataset"))

        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        try:
            df = load_dataset(filepath)
            valid, msg = validate_dataset_columns(df.columns)
            if not valid:
                os.remove(filepath)
                flash(msg, "danger")
                return redirect(url_for("admin.upload_dataset"))

            df = clean_data(df)
            rows = len(df)
            Dataset.query.update({Dataset.is_active: False})
            ds = Dataset(filename=filename, rows=rows, uploaded_by=current_user.id, is_active=True)
            db.session.add(ds)
            db.session.commit()
            generate_eda(df, current_app.config["PLOT_FOLDER"])
            log_audit("upload_dataset", "dataset", filename)
            flash(f"Dataset '{filename}' uploaded ({rows} rows). Schema validated.", "success")
        except Exception as e:
            flash(f"Error processing dataset: {e}", "danger")

    return render_template("admin/upload_dataset.html")


@admin_bp.route("/eda")
@login_required
@role_required("admin")
def eda():
    active = Dataset.query.filter_by(is_active=True).first()
    eda_results = None
    if active:
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], active.filename)
        if os.path.exists(filepath):
            df = clean_data(load_dataset(filepath))
            eda_results = generate_eda(df, current_app.config["PLOT_FOLDER"])
    return render_template("admin/eda.html", active_dataset=active, eda_results=eda_results)


@admin_bp.route("/eda/export-pdf")
@login_required
@role_required("admin")
def export_eda_pdf():
    active = Dataset.query.filter_by(is_active=True).first()
    if not active:
        flash("No active dataset.", "warning")
        return redirect(url_for("admin.eda"))
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], active.filename)
    df = clean_data(load_dataset(filepath))
    eda_results = generate_eda(df, current_app.config["PLOT_FOLDER"])
    pdf = generate_eda_pdf(eda_results, active.filename)
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name="eda_report.pdf")


@admin_bp.route("/train-models", methods=["GET", "POST"])
@login_required
@role_required("admin")
def train_models():
    active = Dataset.query.filter_by(is_active=True).first()
    if request.method == "POST":
        if not active:
            flash("No active dataset. Upload a dataset first.", "warning")
            return redirect(url_for("admin.upload_dataset"))

        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], active.filename)
        df = clean_data(load_dataset(filepath))

        job = TrainingJob(
            job_type="standard_train",
            dataset_filename=active.filename,
            rows_used=len(df),
            status="running",
        )
        db.session.add(job)
        db.session.flush()

        results, best_model = train_all_models(
            df, current_app.config["MODEL_FOLDER"],
            test_size=current_app.config["TRAIN_TEST_SPLIT"],
            random_state=current_app.config["RANDOM_STATE"],
        )
        clear_model_cache()
        ModelMetrics.query.delete()
        for r in results:
            db.session.add(ModelMetrics(
                model_name=r["model_name"],
                accuracy=r["accuracy"], precision=r["precision"],
                recall=r["recall"], f1_score=r["f1_score"],
                confusion_matrix=json.dumps(r["confusion_matrix"]),
                confusion_matrix_plot=r.get("confusion_matrix_plot"),
                is_best=r["is_best"], training_job_id=job.id,
            ))
        job.best_model = best_model
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        production = "Logistic Regression" if "Logistic Regression" in MODEL_BUILDERS else best_model
        set_production_model_name(production)
        db.session.commit()
        log_audit("train_models", "ml", f"best={best_model}, production={production}")
        flash(f"Models trained. Best (ROC-AUC): {best_model}. Predictions use: {production}.", "success")
        return redirect(url_for("admin.train_models"))

    metrics = ModelMetrics.query.order_by(ModelMetrics.f1_score.desc()).all()
    return render_template("admin/train_models.html", metrics=metrics)


@admin_bp.route("/retrain-feedback", methods=["POST"])
@login_required
@role_required("admin")
def retrain_feedback():
    try:
        results, best_model, fb_count = retrain_with_feedback(
            current_app.config["MODEL_FOLDER"],
            current_app.config["UPLOAD_FOLDER"],
            test_size=current_app.config["TRAIN_TEST_SPLIT"],
            random_state=current_app.config["RANDOM_STATE"],
        )
        clear_model_cache()
        log_audit("retrain_feedback", "ml", f"feedback_rows={fb_count}, best={best_model}")
        flash(f"Retrained with {fb_count} feedback rows. Best model: {best_model}", "success")
    except Exception as e:
        flash(f"Retraining failed: {e}", "danger")
    return redirect(url_for("admin.view_feedback"))


@admin_bp.route("/model-settings", methods=["GET", "POST"])
@login_required
@role_required("admin")
def model_settings():
    form = ModelSelectForm()
    form.production_model.choices = [(n, n) for n in MODEL_BUILDERS]
    if form.validate_on_submit():
        set_production_model_name(form.production_model.data)
        clear_model_cache()
        log_audit("set_production_model", "ml", form.production_model.data)
        flash(f"Production model set to {form.production_model.data}.", "success")
        return redirect(url_for("admin.model_settings"))
    current = get_production_model_name()
    if current:
        form.production_model.data = current
    metrics = ModelMetrics.query.order_by(ModelMetrics.f1_score.desc()).all()
    return render_template("admin/model_settings.html", form=form, metrics=metrics, current=current)


@admin_bp.route("/users")
@login_required
@role_required("admin")
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    if form.validate_on_submit():
        user.full_name = form.full_name.data
        user.email = form.email.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        db.session.commit()
        log_audit("edit_user", "user", f"id={user_id}")
        flash("User updated.", "success")
        return redirect(url_for("admin.manage_users"))
    return render_template("admin/edit_user.html", form=form, user=user)


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["GET", "POST"])
@login_required
@role_required("admin")
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        log_audit("reset_password", "user", f"id={user_id}")
        flash("Password reset successfully.", "success")
        return redirect(url_for("admin.manage_users"))
    return render_template("admin/reset_password.html", form=form, user=user)


@admin_bp.route("/assignments", methods=["GET", "POST"])
@login_required
@role_required("admin")
def manage_assignments():
    providers = User.query.filter_by(role="provider", is_active=True).all()
    patients = User.query.filter_by(role="patient", is_active=True).all()
    assignments = ProviderPatient.query.all()
    form = AssignDoctorPatientForm()
    form.provider_id.choices = [(p.id, f"{p.full_name} (@{p.username})") for p in providers]
    form.patient_id.choices = [(p.id, f"{p.full_name} (@{p.username})") for p in patients]

    if form.validate_on_submit():
        provider_id = form.provider_id.data
        patient_id = form.patient_id.data
        if ProviderPatient.query.filter_by(provider_id=provider_id, patient_id=patient_id).first():
            flash("This patient is already assigned to that doctor.", "warning")
        else:
            db.session.add(ProviderPatient(provider_id=provider_id, patient_id=patient_id))
            db.session.commit()
            provider = User.query.get(provider_id)
            patient = User.query.get(patient_id)
            log_audit("assign_patient", "assignment", f"doctor={provider.username}, patient={patient.username}")
            flash(f"Success! {patient.full_name} is now assigned to {provider.full_name}.", "success")
        return redirect(url_for("admin.manage_assignments"))

    return render_template(
        "admin/assignments.html",
        form=form,
        providers=providers, patients=patients, assignments=assignments,
    )


@admin_bp.route("/assignments/<int:assignment_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_assignment(assignment_id):
    row = ProviderPatient.query.get_or_404(assignment_id)
    db.session.delete(row)
    db.session.commit()
    flash("Doctor–patient link removed.", "info")
    return redirect(url_for("admin.manage_assignments"))


@admin_bp.route("/education")
@login_required
@role_required("admin")
def manage_education():
    resources = EducationResource.query.order_by(EducationResource.category).all()
    return render_template("admin/education.html", resources=resources)


@admin_bp.route("/education/add", methods=["GET", "POST"])
@admin_bp.route("/education/<int:resource_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_education(resource_id=None):
    resource = EducationResource.query.get(resource_id) if resource_id else None
    form = EducationForm(obj=resource)
    if form.validate_on_submit():
        if not resource:
            resource = EducationResource()
            db.session.add(resource)
        resource.title = form.title.data
        resource.category = form.category.data
        resource.content = form.content.data
        resource.external_url = form.external_url.data or None
        db.session.commit()
        flash("Education resource saved.", "success")
        return redirect(url_for("admin.manage_education"))
    return render_template("admin/edit_education.html", form=form, resource=resource)


@admin_bp.route("/education/<int:resource_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_education(resource_id):
    resource = EducationResource.query.get_or_404(resource_id)
    db.session.delete(resource)
    db.session.commit()
    flash("Resource deleted.", "info")
    return redirect(url_for("admin.manage_education"))


@admin_bp.route("/feedback")
@login_required
@role_required("admin")
def view_feedback():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    pending = Feedback.query.filter_by(used_in_training=False).filter(
        Feedback.actual_outcome.isnot(None)
    ).count()
    return render_template(
        "admin/feedback.html",
        feedbacks=feedbacks,
        pending=pending,
        unread_count=get_unread_admin_feedback_count(),
    )


@admin_bp.route("/feedback/<int:feedback_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def view_feedback_detail(feedback_id):
    fb = Feedback.query.get_or_404(feedback_id)
    if request.method == "GET" and not fb.is_read:
        fb.is_read = True
        db.session.commit()
        log_audit("read_patient_feedback", "feedback", f"id={feedback_id}")
    prediction = fb.prediction
    record = HealthRecord.query.get(prediction.health_record_id) if prediction else None
    return render_template(
        "admin/feedback_detail.html",
        feedback=fb,
        prediction=prediction,
        record=record,
    )


@admin_bp.route("/feedback/<int:feedback_id>/mark-read", methods=["POST"])
@login_required
@role_required("admin")
def mark_feedback_read(feedback_id):
    fb = Feedback.query.get_or_404(feedback_id)
    fb.is_read = True
    db.session.commit()
    flash("Feedback marked as read.", "success")
    return redirect(url_for("admin.view_feedback"))


@admin_bp.route("/feedback/mark-all-read", methods=["POST"])
@login_required
@role_required("admin")
def mark_all_feedback_read():
    Feedback.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All patient feedback marked as read.", "success")
    return redirect(url_for("admin.view_feedback"))


@admin_bp.route("/audit-logs")
@login_required
@role_required("admin")
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("admin/audit_logs.html", logs=logs)


@admin_bp.route("/training-history")
@login_required
@role_required("admin")
def training_history():
    jobs = TrainingJob.query.order_by(TrainingJob.started_at.desc()).all()
    return render_template("admin/training_history.html", jobs=jobs)


@admin_bp.route("/received-reports")
@login_required
@role_required("admin")
def received_reports():
    reports = AdminReportSubmission.query.order_by(
        AdminReportSubmission.created_at.desc()
    ).all()
    return render_template(
        "admin/received_reports.html",
        reports=reports,
        unread_count=get_unread_admin_reports_count(),
    )


@admin_bp.route("/received-reports/<int:report_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def view_received_report(report_id):
    report = AdminReportSubmission.query.get_or_404(report_id)
    doctors = User.query.filter_by(role="provider", is_active=True).order_by(User.full_name).all()
    existing_forwards = DoctorReportForward.query.filter_by(admin_report_id=report.id).all()
    already_sent_ids = {f.provider_id for f in existing_forwards}

    forward_form = ForwardReportToDoctorsForm()
    forward_form.provider_ids.choices = [
        (d.id, f"{d.full_name} (@{d.username})") for d in doctors if d.id not in already_sent_ids
    ]

    try:
        if request.method == "GET" and not report.is_read:
            report.is_read = True
            db.session.commit()
            log_audit("read_admin_report", "admin_report", f"id={report_id}")

        if forward_form.validate_on_submit():
            if not forward_form.provider_ids.data:
                flash("Please select at least one doctor.", "warning")
            else:
                sent_names = []
                for provider_id in forward_form.provider_ids.data:
                    doctor = User.query.get(provider_id)
                    if not doctor or doctor.role != "provider" or not doctor.is_active:
                        continue
                    if DoctorReportForward.query.filter_by(
                        admin_report_id=report.id, provider_id=provider_id
                    ).first():
                        continue
                    db.session.add(DoctorReportForward(
                        admin_report_id=report.id,
                        provider_id=provider_id,
                        forwarded_by=current_user.id,
                        admin_note=forward_form.admin_note.data,
                        is_read=False,
                    ))
                    sent_names.append(doctor.full_name)
                db.session.commit()
                if sent_names:
                    log_audit(
                        "forward_report_to_doctors", "admin_report",
                        f"report_id={report.id}, doctors={','.join(sent_names)}",
                    )
                    flash(
                        f"Report sent to {len(sent_names)} doctor(s): {', '.join(sent_names)}.",
                        "success",
                    )
                else:
                    flash("No new doctors were selected or all were already sent this report.", "warning")
                return redirect(url_for("admin.view_received_report", report_id=report.id))

        display = parse_admin_report_display_data(report)
        return render_template(
            "admin/report_detail.html",
            report=report,
            forward_form=forward_form,
            doctors=doctors,
            existing_forwards=existing_forwards,
            already_sent_ids=already_sent_ids,
            **display,
        )
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Failed to open admin report %s", report_id)
        flash(f"Could not open this report: {exc}", "danger")
        return redirect(url_for("admin.received_reports"))


@admin_bp.route("/received-reports/<int:report_id>/mark-read", methods=["POST"])
@login_required
@role_required("admin")
def mark_report_read(report_id):
    report = AdminReportSubmission.query.get_or_404(report_id)
    report.is_read = True
    db.session.commit()
    flash("Report marked as read.", "success")
    return redirect(url_for("admin.received_reports"))


@admin_bp.route("/received-reports/mark-all-read", methods=["POST"])
@login_required
@role_required("admin")
def mark_all_reports_read():
    AdminReportSubmission.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All patient reports marked as read.", "success")
    return redirect(url_for("admin.received_reports"))
