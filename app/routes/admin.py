import json
import os
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.decorators import role_required
from app.forms import (
    AssignDoctorPatientForm, CreateUserForm, DatasetUploadForm, EducationForm,
    ModelSelectForm, ResetPasswordForm, UserEditForm,
)
from app.ml.pipeline import MODEL_BUILDERS, clean_data, generate_eda, load_dataset, train_all_models
from app.ml.predictor import clear_model_cache
from app.ml.retrain import retrain_with_feedback
from app.ml.validators import validate_dataset_columns
from app.ml.reports import generate_eda_pdf
from app.models import (
    Dataset, EducationResource,
    Feedback, HealthRecord, ModelMetrics, ProviderPatient, TrainingJob, User,
)
from app.utils import (
    get_production_model_name, get_unread_admin_feedback_count,
    log_audit, set_production_model_name,
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
        unread_feedback=get_unread_admin_feedback_count(),
        jobs=jobs,
        production_model=get_production_model_name(),
        patients=User.query.filter_by(role="patient").order_by(User.created_at.desc()).all(),
        providers=User.query.filter_by(role="provider").order_by(User.created_at.desc()).all(),
    )


def _activate_dataset(filename, rows):
    for existing in Dataset.query.filter_by(is_active=True).all():
        existing.is_active = False
    ds = Dataset(
        filename=filename,
        rows=rows,
        uploaded_by=current_user.id,
        is_active=True,
    )
    db.session.add(ds)
    db.session.commit()
    return ds


def _process_dataset_file(filepath, filename):
    """Validate, activate, and run EDA. Returns (ok: bool, message: str)."""
    df = load_dataset(filepath)
    valid, msg = validate_dataset_columns(df.columns)
    if not valid:
        return False, msg
    df = clean_data(df)
    rows = len(df)
    if rows < 10:
        return False, "Dataset must contain at least 10 valid rows after cleaning."
    _activate_dataset(filename, rows)
    try:
        generate_eda(df, current_app.config["PLOT_FOLDER"])
    except Exception as eda_err:
        log_audit("upload_dataset", "dataset", f"{filename} (EDA warning: {eda_err})")
        return True, (
            f"Dataset '{filename}' imported ({rows} rows), but EDA charts failed: {eda_err}. "
            "You can still train models."
        )
    log_audit("upload_dataset", "dataset", filename)
    return True, f"Dataset '{filename}' imported successfully ({rows} rows). Schema validated."


@admin_bp.route("/upload-dataset", methods=["GET", "POST"])
@login_required
@role_required("admin")
def upload_dataset():
    form = DatasetUploadForm()
    active = Dataset.query.filter_by(is_active=True).order_by(Dataset.uploaded_at.desc()).first()
    datasets = Dataset.query.order_by(Dataset.uploaded_at.desc()).limit(10).all()

    if form.validate_on_submit():
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)

        # One-click: load built-in Pima diabetes CSV already in the project.
        if form.use_sample.data:
            sample_name = "diabetes.csv"
            sample_path = os.path.join(upload_dir, sample_name)
            if not os.path.exists(sample_path):
                flash(
                    "Built-in sample not found. Place diabetes.csv in the data/ folder, "
                    "or upload a CSV manually.",
                    "danger",
                )
                return redirect(url_for("admin.upload_dataset"))
            try:
                ok, message = _process_dataset_file(sample_path, sample_name)
                flash(message, "success" if ok else "danger")
                return redirect(url_for("admin.eda") if ok else url_for("admin.upload_dataset"))
            except Exception as e:
                flash(f"Error loading sample dataset: {e}", "danger")
                return redirect(url_for("admin.upload_dataset"))

        file = form.dataset.data or request.files.get("dataset")
        if not file or not getattr(file, "filename", None):
            flash("Please choose a CSV file, or click Load Built-in Sample Dataset.", "danger")
            return redirect(url_for("admin.upload_dataset"))

        original = file.filename
        if not original.lower().endswith(".csv"):
            flash("Please upload a .csv file (Excel .xlsx is not supported).", "danger")
            return redirect(url_for("admin.upload_dataset"))

        filename = secure_filename(original) or "uploaded_dataset.csv"
        if not filename.lower().endswith(".csv"):
            filename += ".csv"
        filepath = os.path.join(upload_dir, filename)
        try:
            file.save(filepath)
            ok, message = _process_dataset_file(filepath, filename)
            if not ok:
                if os.path.exists(filepath) and filename != "diabetes.csv":
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
                flash(message, "danger")
                return redirect(url_for("admin.upload_dataset"))
            flash(message, "success" if "successfully" in message else "warning")
            return redirect(url_for("admin.eda"))
        except Exception as e:
            flash(f"Error processing dataset: {e}", "danger")
            return redirect(url_for("admin.upload_dataset"))

    return render_template(
        "admin/upload_dataset.html",
        form=form,
        active=active,
        datasets=datasets,
    )


@admin_bp.route("/eda")
@login_required
@role_required("admin")
def eda():
    active = Dataset.query.filter_by(is_active=True).first()
    eda_results = None
    preprocess_info = None
    if active:
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], active.filename)
        if os.path.exists(filepath):
            df_raw = load_dataset(filepath)
            df = clean_data(df_raw)
            eda_results = generate_eda(df, current_app.config["PLOT_FOLDER"])
            n = len(df)
            train_n = int(n * (1 - current_app.config["TRAIN_TEST_SPLIT"]))
            test_n = n - train_n
            preprocess_info = {
                "raw_rows": len(df_raw),
                "clean_rows": n,
                "steps": [
                    "Replace zeros with NaN in Glucose, BP, SkinThickness, Insulin, BMI",
                    "Impute missing values with column median",
                    "StandardScaler normalization on numeric features",
                    f"Random 70/30 stratified train-test split ({train_n} train / {test_n} test)",
                ],
                "train_pct": 70,
                "test_pct": 30,
            }
    return render_template(
        "admin/eda.html",
        active_dataset=active,
        eda_results=eda_results,
        preprocess_info=preprocess_info,
    )


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


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already exists.", "danger")
        elif User.query.filter_by(email=form.email.data).first():
            flash("Email already registered.", "danger")
        elif form.role.data == "provider" and not (form.professional_credentials.data or "").strip():
            flash("Healthcare providers require professional credentials.", "danger")
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                full_name=form.full_name.data,
                role=form.role.data,
                professional_credentials=(form.professional_credentials.data or "").strip() or None,
                security_question="city",
                is_active=True,
            )
            user.set_password(form.password.data)
            user.set_security_answer(form.username.data)
            db.session.add(user)
            db.session.commit()
            log_audit("create_user", "user", f"username={user.username}, role={user.role}")
            flash(f"User '{user.username}' created.", "success")
            return redirect(url_for("admin.manage_users"))
    return render_template("admin/create_user.html", form=form)


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
        user.professional_credentials = (form.professional_credentials.data or "").strip() or None
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
    providers = User.query.filter_by(role="provider").order_by(User.full_name.asc()).all()
    patients = User.query.filter_by(role="patient").order_by(User.created_at.desc()).all()
    assignments = ProviderPatient.query.all()
    form = AssignDoctorPatientForm()
    form.provider_id.choices = [
        (p.id, f"{p.full_name} (@{p.username})" + ("" if p.is_active else " [inactive]"))
        for p in providers
    ]
    form.patient_id.choices = [
        (p.id, f"{p.full_name} (@{p.username})" + ("" if p.is_active else " [inactive]"))
        for p in patients
    ]

    if form.validate_on_submit():
        provider_id = form.provider_id.data
        patient_id = form.patient_id.data
        if ProviderPatient.query.filter_by(provider_id=provider_id, patient_id=patient_id).first():
            flash("This patient is already assigned to that healthcare provider.", "warning")
        else:
            db.session.add(ProviderPatient(provider_id=provider_id, patient_id=patient_id))
            db.session.commit()
            provider = User.query.get(provider_id)
            patient = User.query.get(patient_id)
            log_audit(
                "assign_patient",
                "assignment",
                f"provider={provider.username}, patient={patient.username}",
            )
            flash(
                f"{patient.full_name} is now assigned to {provider.full_name}. "
                "The provider will see this patient under Clinical.",
                "success",
            )
        return redirect(url_for("admin.manage_assignments"))

    return render_template(
        "admin/assignments.html",
        form=form,
        providers=providers,
        patients=patients,
        assignments=assignments,
    )


@admin_bp.route("/assignments/<int:assignment_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_assignment(assignment_id):
    row = ProviderPatient.query.get_or_404(assignment_id)
    db.session.delete(row)
    db.session.commit()
    flash("Patient–provider link removed.", "info")
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


@admin_bp.route("/training-history")
@login_required
@role_required("admin")
def training_history():
    jobs = TrainingJob.query.order_by(TrainingJob.started_at.desc()).all()
    return render_template("admin/training_history.html", jobs=jobs)
