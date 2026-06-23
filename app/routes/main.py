import json
from io import BytesIO

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app import db
from app.decorators import role_required
from app.forms import FeedbackForm, HealthDataForm, SendReportToAdminForm
from app.ml.predictor import predict_health_record, resolve_model_name
from app.ml.recommendations import parse_stored_recommendations
from app.ml.reports import generate_csv_report, generate_pdf_report
from app.models import AdminReportSubmission, DoctorReportRemark, EducationResource, Feedback, HealthRecord, ModelMetrics, Prediction
from app.utils import (
    build_admin_report_snapshot, get_patient_doctor_remarks, get_unread_doctor_remarks_count,
    log_audit, redirect_to_role_home,
)

main_bp = Blueprint("main", __name__)


def _health_form_context():
    import json
    from app.health_fields import HEALTH_FIELD_INFO, HEALTHY_EXAMPLE
    return {
        "field_info": HEALTH_FIELD_INFO,
        "averages_json": json.dumps({k: v["average"] for k, v in HEALTH_FIELD_INFO.items()}),
        "healthy_example_json": json.dumps(HEALTHY_EXAMPLE),
    }


def _populate_health_form(form, record):
    form.sex.data = getattr(record, "sex", None) or "female"
    form.pregnancies.data = min(record.pregnancies, 6)
    form.glucose.data = record.glucose
    form.systolic.data = getattr(record, "systolic", None) or (record.blood_pressure + 40 if record.blood_pressure else 120)
    form.diastolic.data = getattr(record, "diastolic", None) or record.blood_pressure or 80
    form.skin_thickness.data = record.skin_thickness
    form.insulin.data = record.insulin
    form.bmi.data = record.bmi
    form.diabetes_pedigree.data = 1 if (record.diabetes_pedigree or 0) >= 0.5 else 0
    form.age.data = record.age


def _apply_form_to_record(form, record):
    record.sex = form.sex.data
    record.pregnancies = 0 if form.sex.data == "male" else int(form.pregnancies.data or 0)
    record.glucose = form.glucose.data
    record.systolic = form.systolic.data
    record.diastolic = form.diastolic.data
    record.blood_pressure = form.diastolic.data
    record.skin_thickness = form.skin_thickness.data
    record.insulin = form.insulin.data
    record.bmi = form.bmi.data
    # Map yes/no family history to realistic Pima-scale pedigree values.
    record.diabetes_pedigree = 0.65 if int(form.diabetes_pedigree.data or 0) == 1 else 0.28
    record.age = form.age.data


def _run_prediction_for_record(record):
    result = predict_health_record(
        record, current_app.config["MODEL_FOLDER"], for_patient=True,
    )
    prediction = Prediction.query.filter_by(health_record_id=record.id).first()
    if not prediction:
        prediction = Prediction(user_id=record.user_id, health_record_id=record.id)
        db.session.add(prediction)
    prediction.model_name = result["model_name"]
    prediction.probability = result["probability"]
    prediction.risk_level = result["risk_level"]
    prediction.explanation = result["explanation"]
    prediction.recommendations = result["recommendations"]
    return prediction, result


@main_bp.route("/health")
def health():
    return {"ok": True, "service": "diabetes-risk-predictor"}, 200


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect_to_role_home()
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin.admin_dashboard"))
    if current_user.is_provider:
        return redirect(url_for("provider.provider_dashboard"))

    records = HealthRecord.query.filter_by(user_id=current_user.id).order_by(
        HealthRecord.recorded_at.desc()
    ).all()
    predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(
        Prediction.created_at.desc()
    ).all()
    sent_reports = AdminReportSubmission.query.filter_by(
        patient_id=current_user.id
    ).order_by(AdminReportSubmission.created_at.desc()).all()
    doctor_remarks = get_patient_doctor_remarks(current_user.id)
    unread_remarks = get_unread_doctor_remarks_count(current_user.id)
    metrics = ModelMetrics.query.order_by(ModelMetrics.trained_at.desc()).all()
    trend_data = [
        {"date": p.created_at.strftime("%Y-%m-%d"), "probability": round(p.probability * 100, 1)}
        for p in reversed(predictions)
    ]
    alert = None
    if len(predictions) >= 2 and predictions[0].probability > predictions[1].probability:
        alert = "Your diabetes risk has increased since your last assessment. Consider consulting your healthcare provider."
    latest_rec = parse_stored_recommendations(predictions[0]) if predictions else None
    return render_template(
        "dashboard.html", records=records, predictions=predictions,
        sent_reports=sent_reports,
        doctor_remarks=doctor_remarks,
        unread_remarks=unread_remarks,
        metrics=metrics, trend_data=trend_data, alert=alert,
        recommendation_plan=latest_rec,
    )


@main_bp.route("/health-data", methods=["GET", "POST"])
@login_required
@role_required("patient")
def health_data():
    form = HealthDataForm()
    latest_prediction = None
    scored_record = None
    ctx = _health_form_context()

    if form.validate_on_submit():
        record = HealthRecord(user_id=current_user.id)
        _apply_form_to_record(form, record)
        db.session.add(record)
        db.session.flush()
        try:
            latest_prediction, result = _run_prediction_for_record(record)
            scored_record = record
            db.session.commit()
            log_audit("prediction", "health_record", f"risk={result['risk_level']}")
            flash(
                f"Prediction complete: {result['probability'] * 100:.1f}% diabetes risk "
                f"({result['risk_level']}) using glucose {record.glucose:.0f}, BMI {record.bmi:.1f}.",
                "success",
            )
        except FileNotFoundError as e:
            db.session.commit()
            flash(str(e), "warning")
    rec_plan = None
    if latest_prediction:
        rec_plan = parse_stored_recommendations(latest_prediction)
    return render_template(
        "health_data.html", form=form, prediction=latest_prediction,
        scored_record=scored_record,
        recommendation_plan=rec_plan, **ctx,
    )


@main_bp.route("/my-health-records")
@login_required
@role_required("patient")
def my_health_records():
    records = HealthRecord.query.filter_by(user_id=current_user.id).order_by(
        HealthRecord.recorded_at.desc()
    ).all()
    predictions = Prediction.query.filter_by(user_id=current_user.id).all()
    pred_map = {p.health_record_id: p for p in predictions}
    return render_template("my_health_records.html", records=records, pred_map=pred_map)


@main_bp.route("/my-health-records/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("patient")
def edit_health_record(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if record.user_id != current_user.id:
        abort(403)

    form = HealthDataForm()
    ctx = _health_form_context()
    latest_prediction = None

    if request.method == "GET":
        _populate_health_form(form, record)

    if form.validate_on_submit():
        _apply_form_to_record(form, record)
        try:
            latest_prediction, result = _run_prediction_for_record(record)
            db.session.commit()
            log_audit("update_health_record", "health_record", f"id={record_id}, risk={result['risk_level']}")
            flash("Health values updated and diabetes prediction recalculated.", "success")
        except FileNotFoundError as e:
            db.session.commit()
            flash(str(e), "warning")

    pred = latest_prediction or Prediction.query.filter_by(health_record_id=record.id).first()
    return render_template(
        "health_data.html",
        form=form,
        prediction=pred,
        scored_record=record if latest_prediction else None,
        recommendation_plan=parse_stored_recommendations(pred) if pred else None,
        edit_mode=True,
        page_title="Update Your Health Values",
        page_subtitle="Change your numbers below and save to get a new diabetes probability.",
        submit_label="Update & Recalculate Diabetes Risk",
        **ctx,
    )


@main_bp.route("/prediction/<int:prediction_id>")
@login_required
def prediction_detail(prediction_id):
    prediction = Prediction.query.get_or_404(prediction_id)
    if prediction.user_id != current_user.id and not current_user.is_provider and not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.dashboard"))
    explanation = json.loads(prediction.explanation) if prediction.explanation else []
    record = HealthRecord.query.get(prediction.health_record_id)
    return render_template(
        "prediction_detail.html",
        prediction=prediction,
        explanation=explanation,
        record=record,
        recommendation_plan=parse_stored_recommendations(prediction),
    )


@main_bp.route("/education")
@login_required
def education():
    resources = EducationResource.query.all()
    grouped = {}
    for r in resources:
        grouped.setdefault(r.category, []).append(r)
    return render_template("education.html", grouped=grouped)


@main_bp.route("/feedback", methods=["GET", "POST"])
@login_required
@role_required("patient")
def feedback():
    form = FeedbackForm()
    if current_user.is_patient:
        preds = Prediction.query.filter_by(user_id=current_user.id).order_by(
            Prediction.created_at.desc()
        ).limit(20).all()
    else:
        preds = Prediction.query.order_by(Prediction.created_at.desc()).limit(20).all()
    form.prediction_id.choices = [
        (p.id, f"{p.created_at.strftime('%Y-%m-%d')} - {p.risk_level} ({p.probability:.0%})")
        for p in preds
    ]
    if not form.prediction_id.choices:
        flash("No predictions available to review.", "info")

    if form.validate_on_submit():
        fb = Feedback(
            user_id=current_user.id,
            prediction_id=form.prediction_id.data,
            rating=int(form.rating.data),
            comment=form.comment.data,
            actual_outcome=int(form.actual_outcome.data) if form.actual_outcome.data else None,
            is_read=False,
        )
        db.session.add(fb)
        db.session.commit()
        log_audit("send_feedback_to_admin", "feedback", f"prediction_id={form.prediction_id.data}")
        flash("Your feedback has been sent to the administrator. Thank you!", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("feedback.html", form=form)


@main_bp.route("/send-report-to-admin", methods=["GET", "POST"])
@login_required
@role_required("patient")
def send_report_to_admin():
    form = SendReportToAdminForm()
    predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(
        Prediction.created_at.desc()
    ).limit(20).all()
    form.prediction_id.choices = [
        (
            p.id,
            f"{p.created_at.strftime('%Y-%m-%d')} — {p.risk_level} risk ({p.probability:.0%})",
        )
        for p in predictions
    ]

    if not form.prediction_id.choices:
        flash("No predictions yet. Add health data first, then send your report to admin.", "info")
        return redirect(url_for("main.health_data"))

    if request.args.get("prediction_id"):
        try:
            selected_id = int(request.args.get("prediction_id"))
            if any(p.id == selected_id for p in predictions):
                form.prediction_id.data = selected_id
        except (TypeError, ValueError):
            pass

    if form.validate_on_submit():
        prediction = Prediction.query.get_or_404(form.prediction_id.data)
        if prediction.user_id != current_user.id:
            abort(403)
        record = HealthRecord.query.get(prediction.health_record_id)
        submission = AdminReportSubmission(
            patient_id=current_user.id,
            prediction_id=prediction.id,
            message=form.message.data,
            report_summary=build_admin_report_snapshot(
                current_user, prediction, record, form.message.data
            ),
            is_read=False,
        )
        db.session.add(submission)
        db.session.commit()
        log_audit("send_report_to_admin", "admin_report", f"prediction_id={prediction.id}")
        flash("Your report was sent to the admin successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("send_report_to_admin.html", form=form)


@main_bp.route("/notifications")
@login_required
@role_required("patient")
def patient_notifications():
    remarks = get_patient_doctor_remarks(current_user.id)
    return render_template(
        "patient_notifications.html",
        remarks=remarks,
        unread_count=get_unread_doctor_remarks_count(current_user.id),
    )


@main_bp.route("/notifications/<int:remark_id>", methods=["GET", "POST"])
@login_required
@role_required("patient")
def view_doctor_remark(remark_id):
    remark = DoctorReportRemark.query.get_or_404(remark_id)
    if remark.patient_id != current_user.id:
        abort(403)

    if not remark.is_read:
        remark.is_read = True
        db.session.commit()

    prediction = remark.prediction
    feedback_form = FeedbackForm()
    feedback_form.prediction_id.choices = [
        (prediction.id, f"{prediction.created_at.strftime('%Y-%m-%d')} - {prediction.risk_level} ({prediction.probability:.0%})"),
    ]
    feedback_form.prediction_id.data = prediction.id

    if request.method == "POST" and not remark.feedback_submitted:
        if feedback_form.validate_on_submit():
            fb = Feedback(
                user_id=current_user.id,
                prediction_id=feedback_form.prediction_id.data,
                rating=int(feedback_form.rating.data),
                comment=feedback_form.comment.data,
                actual_outcome=int(feedback_form.actual_outcome.data) if feedback_form.actual_outcome.data else None,
                is_read=False,
            )
            db.session.add(fb)
            remark.feedback_submitted = True
            db.session.commit()
            log_audit("send_feedback_to_admin", "feedback", f"remark_id={remark_id}")
            flash("Your feedback has been sent to the administrator. Thank you!", "success")
            return redirect(url_for("main.dashboard"))

    return render_template(
        "doctor_remark_detail.html",
        remark=remark,
        prediction=prediction,
        feedback_form=feedback_form,
    )


@main_bp.route("/reports/csv")
@login_required
@role_required("patient")
def export_csv():
    predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()
    records = HealthRecord.query.filter_by(user_id=current_user.id).all()
    csv_data = generate_csv_report(current_user, predictions, records)
    log_audit("export_csv", "report")
    return send_file(
        BytesIO(csv_data.encode("utf-8")), mimetype="text/csv",
        as_attachment=True, download_name=f"diabetes_report_{current_user.username}.csv",
    )


@main_bp.route("/reports/pdf")
@login_required
@role_required("patient")
def export_pdf():
    predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()
    records = HealthRecord.query.filter_by(user_id=current_user.id).all()
    metrics = ModelMetrics.query.order_by(ModelMetrics.f1_score.desc()).all()
    pdf_buffer = generate_pdf_report(current_user, predictions, records, metrics)
    log_audit("export_pdf", "report")
    return send_file(
        pdf_buffer, mimetype="application/pdf",
        as_attachment=True, download_name=f"diabetes_report_{current_user.username}.pdf",
    )


@main_bp.route("/progress")
@login_required
@role_required("patient")
def progress():
    records = HealthRecord.query.filter_by(user_id=current_user.id).order_by(HealthRecord.recorded_at.asc()).all()
    predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.asc()).all()
    pred_by_record = {p.health_record_id: p for p in predictions}
    chart_data = {
        "dates": [r.recorded_at.strftime("%Y-%m-%d") for r in records],
        "glucose": [r.glucose for r in records],
        "bmi": [r.bmi for r in records],
        "risk": [round(pred_by_record[r.id].probability * 100, 1) if r.id in pred_by_record else None for r in records],
    }
    history = []
    for r in records:
        p = pred_by_record.get(r.id)
        history.append({"record": r, "prediction": p})
    alert = None
    risks = [p.probability for p in predictions if p]
    if len(risks) >= 2 and risks[-1] > risks[-2]:
        alert = "Risk trend is increasing. Review your health metrics and consult your provider."
    return render_template("progress.html", history=history, chart_data=chart_data, alert=alert)
