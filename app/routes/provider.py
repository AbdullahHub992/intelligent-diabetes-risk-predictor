import json
from io import BytesIO

from flask import Blueprint, flash, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required

from app import db
from app.decorators import role_required
from app.forms import ClinicalNoteForm
from app.ml.recommendations import parse_stored_recommendations
from app.ml.reports import generate_csv_report, generate_pdf_report
from app.models import ClinicalNote, HealthRecord, ModelMetrics, Prediction, User
from app.utils import (
    get_assigned_patient_ids,
    log_audit, provider_can_access_patient,
)

provider_bp = Blueprint("provider", __name__)


def _accessible_patients():
    if current_user.is_admin:
        return User.query.filter_by(role="patient", is_active=True).all()
    ids = get_assigned_patient_ids(current_user.id)
    if not ids:
        return []
    return User.query.filter(User.id.in_(ids), User.is_active == True).all()


@provider_bp.route("/")
@login_required
@role_required("provider", "admin")
def provider_dashboard():
    patients = _accessible_patients()
    patient_ids = [p.id for p in patients]
    if patient_ids:
        recent_predictions = (
            Prediction.query.filter(Prediction.user_id.in_(patient_ids))
            .order_by(Prediction.created_at.desc()).limit(20).all()
        )
    else:
        recent_predictions = []
    high_risk = [p for p in recent_predictions if p.risk_level == "High"]
    risk_trend = [
        {"date": p.created_at.strftime("%Y-%m-%d"), "probability": round(p.probability * 100, 1)}
        for p in reversed(recent_predictions[:10])
    ]
    return render_template(
        "provider/dashboard.html",
        patients=patients,
        recent_predictions=recent_predictions,
        high_risk_count=len(high_risk),
        risk_trend=risk_trend,
    )


@provider_bp.route("/patient/<int:patient_id>")
@login_required
@role_required("provider", "admin")
def patient_detail(patient_id):
    patient = User.query.get_or_404(patient_id)
    if patient.role != "patient":
        flash("Invalid patient.", "danger")
        return redirect(url_for("provider.provider_dashboard"))
    if not provider_can_access_patient(current_user.id, patient_id, current_user.is_admin):
        flash("You are not assigned to this patient.", "danger")
        return redirect(url_for("provider.provider_dashboard"))

    records = HealthRecord.query.filter_by(user_id=patient.id).order_by(HealthRecord.recorded_at.asc()).all()
    predictions = (
        Prediction.query.filter_by(user_id=patient.id)
        .order_by(Prediction.created_at.asc()).all()
    )
    pred_by_record = {p.health_record_id: p for p in predictions}
    chart_data = {
        "dates": [r.recorded_at.strftime("%Y-%m-%d") for r in records],
        "glucose": [r.glucose for r in records],
        "bmi": [r.bmi for r in records],
        "risk": [round(pred_by_record[r.id].probability * 100, 1) if r.id in pred_by_record else 0 for r in records],
    }
    notes = ClinicalNote.query.filter_by(patient_id=patient.id).order_by(ClinicalNote.created_at.desc()).all()
    return render_template(
        "provider/patient_detail.html",
        patient=patient, records=records, predictions=list(reversed(predictions)),
        chart_data=chart_data, notes=notes, pred_by_record=pred_by_record,
    )


@provider_bp.route("/clinical-support/<int:prediction_id>", methods=["GET", "POST"])
@login_required
@role_required("provider", "admin")
def clinical_support(prediction_id):
    prediction = Prediction.query.get_or_404(prediction_id)
    patient = User.query.get(prediction.user_id)
    if not provider_can_access_patient(current_user.id, patient.id, current_user.is_admin):
        flash("Access denied.", "danger")
        return redirect(url_for("provider.provider_dashboard"))

    record = HealthRecord.query.get(prediction.health_record_id)
    explanation = json.loads(prediction.explanation) if prediction.explanation else []
    form = ClinicalNoteForm()

    if form.validate_on_submit():
        note = ClinicalNote(
            provider_id=current_user.id,
            patient_id=patient.id,
            prediction_id=prediction.id,
            note=form.note.data,
        )
        db.session.add(note)
        db.session.commit()
        log_audit("clinical_note", "patient", f"patient_id={patient.id}")
        flash("Clinical note saved.", "success")
        return redirect(url_for("provider.clinical_support", prediction_id=prediction_id))

    notes = ClinicalNote.query.filter_by(prediction_id=prediction.id).order_by(ClinicalNote.created_at.desc()).all()
    return render_template(
        "provider/clinical_support.html",
        prediction=prediction, record=record, patient=patient,
        explanation=explanation, form=form, notes=notes,
        recommendation_plan=parse_stored_recommendations(prediction),
    )


@provider_bp.route("/patient/<int:patient_id>/export/csv")
@login_required
@role_required("provider", "admin")
def export_patient_csv(patient_id):
    patient = User.query.get_or_404(patient_id)
    if not provider_can_access_patient(current_user.id, patient_id, current_user.is_admin):
        flash("Access denied.", "danger")
        return redirect(url_for("provider.provider_dashboard"))
    predictions = Prediction.query.filter_by(user_id=patient.id).order_by(Prediction.created_at.desc()).all()
    records = HealthRecord.query.filter_by(user_id=patient.id).all()
    csv_data = generate_csv_report(patient, predictions, records)
    log_audit("export_csv", "patient", f"patient_id={patient_id}")
    return send_file(
        BytesIO(csv_data.encode("utf-8")), mimetype="text/csv",
        as_attachment=True, download_name=f"report_{patient.username}.csv",
    )


@provider_bp.route("/patient/<int:patient_id>/export/pdf")
@login_required
@role_required("provider", "admin")
def export_patient_pdf(patient_id):
    patient = User.query.get_or_404(patient_id)
    if not provider_can_access_patient(current_user.id, patient_id, current_user.is_admin):
        flash("Access denied.", "danger")
        return redirect(url_for("provider.provider_dashboard"))
    predictions = Prediction.query.filter_by(user_id=patient.id).order_by(Prediction.created_at.desc()).all()
    records = HealthRecord.query.filter_by(user_id=patient.id).all()
    metrics = ModelMetrics.query.order_by(ModelMetrics.f1_score.desc()).all()
    pdf_buffer = generate_pdf_report(patient, predictions, records, metrics)
    log_audit("export_pdf", "patient", f"patient_id={patient_id}")
    return send_file(
        pdf_buffer, mimetype="application/pdf",
        as_attachment=True, download_name=f"report_{patient.username}.pdf",
    )
