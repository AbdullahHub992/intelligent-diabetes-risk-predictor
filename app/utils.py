from flask import redirect, request, url_for
from flask_login import current_user

from app import db
from app.models import AdminReportSubmission, AuditLog, DoctorReportForward, DoctorReportRemark, Feedback, ProviderPatient, SystemConfig


SECURITY_QUESTION_LABELS = {
    "pet": "What is the name of your first pet?",
    "city": "In what city were you born?",
    "school": "What is the name of your primary school?",
    "mother": "What is your mother's maiden name?",
}


def security_question_text(key):
    return SECURITY_QUESTION_LABELS.get(key, key or "Security question")


def role_home_url():
    if not current_user.is_authenticated:
        return url_for("main.index")
    if current_user.is_admin:
        return url_for("admin.admin_dashboard")
    if current_user.is_provider:
        return url_for("provider.provider_dashboard")
    return url_for("main.dashboard")


def redirect_to_role_home():
    return redirect(role_home_url())


def log_audit(action, resource=None, details=None):
    if not current_user.is_authenticated:
        return
    entry = AuditLog(
        user_id=current_user.id,
        action=action,
        resource=resource,
        details=details,
        ip_address=request.remote_addr,
    )
    db.session.add(entry)
    db.session.commit()


def get_production_model_name(default=None):
    cfg = SystemConfig.query.filter_by(key="production_model").first()
    if cfg and cfg.value:
        return cfg.value
    return default


def set_production_model_name(model_name):
    cfg = SystemConfig.query.filter_by(key="production_model").first()
    if cfg:
        cfg.value = model_name
    else:
        db.session.add(SystemConfig(key="production_model", value=model_name))
    db.session.commit()


def _get_config_value(key, default=None):
    cfg = SystemConfig.query.filter_by(key=key).first()
    if cfg and cfg.value:
        return cfg.value
    return default


def _set_config_value(key, value):
    cfg = SystemConfig.query.filter_by(key=key).first()
    if cfg:
        cfg.value = value
    else:
        db.session.add(SystemConfig(key=key, value=value))
    db.session.commit()


OWNER_ACCESS_KEYS = {
    "admin": "owner_admin_access_code",
    "doctor": "owner_doctor_access_code",
}


def get_owner_access_code(portal_key):
    config_key = OWNER_ACCESS_KEYS.get(portal_key)
    if not config_key:
        return None
    return _get_config_value(config_key)


def verify_owner_access_code(portal_key, access_code):
    expected = get_owner_access_code(portal_key)
    if not expected:
        return False
    entered = (access_code or "").strip()
    if not entered:
        return False
    return entered.casefold() == expected.casefold()


def set_owner_access_code(portal_key, access_code):
    config_key = OWNER_ACCESS_KEYS.get(portal_key)
    if config_key:
        _set_config_value(config_key, access_code.strip())


def get_assigned_patient_ids(provider_id):
    rows = ProviderPatient.query.filter_by(provider_id=provider_id).all()
    return [r.patient_id for r in rows]


def provider_can_access_patient(provider_id, patient_id, is_admin=False):
    if is_admin:
        return True
    return ProviderPatient.query.filter_by(
        provider_id=provider_id, patient_id=patient_id
    ).first() is not None


def get_unread_admin_reports_count():
    return AdminReportSubmission.query.filter_by(is_read=False).count()


def get_unread_admin_feedback_count():
    return Feedback.query.filter_by(is_read=False).count()


def get_unread_doctor_forwards_count(provider_id):
    return DoctorReportForward.query.filter_by(provider_id=provider_id, is_read=False).count()


def get_unread_doctor_remarks_count(patient_id):
    return DoctorReportRemark.query.filter_by(patient_id=patient_id, is_read=False).count()


def get_patient_doctor_remarks(patient_id):
    return DoctorReportRemark.query.filter_by(patient_id=patient_id).order_by(
        DoctorReportRemark.created_at.desc()
    ).all()


def parse_admin_report_display_data(report):
    """Build template-friendly dict from an AdminReportSubmission."""
    import json

    from app.ml.recommendations import parse_stored_recommendations

    try:
        summary = json.loads(report.report_summary or "{}")
    except (json.JSONDecodeError, TypeError):
        summary = {}
    if not isinstance(summary, dict):
        summary = {}

    prediction = report.prediction
    health = summary.get("health") if isinstance(summary.get("health"), dict) else {}
    explanation = summary.get("explanation") or []
    if isinstance(explanation, str):
        try:
            explanation = json.loads(explanation)
        except json.JSONDecodeError:
            explanation = []
    if not isinstance(explanation, list):
        explanation = []

    recommendation_plan = None
    if prediction:
        recommendation_plan = parse_stored_recommendations(prediction)
    if not recommendation_plan:
        rec_text = summary.get("recommendations")
        if isinstance(rec_text, str) and rec_text.strip().startswith("{"):
            try:
                recommendation_plan = json.loads(rec_text)
            except json.JSONDecodeError:
                recommendation_plan = None

    return {
        "summary": summary,
        "health": health,
        "explanation": explanation,
        "recommendation_plan": recommendation_plan,
        "prediction": prediction,
    }


def build_admin_report_snapshot(patient, prediction, record, message=None):
    import json

    explanation = []
    if prediction.explanation:
        try:
            explanation = json.loads(prediction.explanation)
        except json.JSONDecodeError:
            explanation = []

    health = None
    if record:
        health = {
            "sex": record.sex,
            "pregnancies": record.pregnancies,
            "glucose": record.glucose,
            "systolic": record.systolic,
            "diastolic": record.diastolic,
            "skin_thickness": record.skin_thickness,
            "insulin": record.insulin,
            "bmi": record.bmi,
            "diabetes_pedigree": record.diabetes_pedigree,
            "age": record.age,
            "recorded_at": record.recorded_at.isoformat() if record.recorded_at else None,
        }

    return json.dumps({
        "patient_name": patient.full_name,
        "patient_username": patient.username,
        "patient_email": patient.email,
        "prediction_date": prediction.created_at.isoformat() if prediction.created_at else None,
        "model_name": prediction.model_name,
        "probability": prediction.probability,
        "risk_level": prediction.risk_level,
        "message": message or "",
        "health": health,
        "explanation": explanation,
        "recommendations": prediction.recommendations,
    })
