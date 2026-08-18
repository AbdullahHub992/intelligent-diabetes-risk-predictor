from flask import redirect, request, url_for
from flask_login import current_user

from app import db
from app.models import AuditLog, Feedback, ProviderPatient, SystemConfig


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


def get_unread_admin_feedback_count():
    return Feedback.query.filter_by(is_read=False).count()
