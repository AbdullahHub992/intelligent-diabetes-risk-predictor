import json
import os
import urllib.request
from datetime import datetime

DEMO_USERNAMES = {"admin", "doctor", "patient"}
BACKUP_BRANCH = os.environ.get("ACCOUNT_BACKUP_BRANCH", "account-backup")
BACKUP_REPO = os.environ.get(
    "ACCOUNT_BACKUP_REPO",
    "AbdullahHub992/intelligent-diabetes-risk-predictor",
)
BACKUP_PATH = "data/live_accounts.json"


def dump_live_accounts():
    from app.models import ProviderPatient, User

    users = []
    for user in User.query.order_by(User.id.asc()).all():
        if user.username in DEMO_USERNAMES:
            continue
        users.append({
            "username": user.username,
            "email": user.email,
            "password_hash": user.password_hash,
            "full_name": user.full_name,
            "role": user.role,
            "professional_credentials": user.professional_credentials,
            "phone": user.phone,
            "address": user.address,
            "is_active": bool(user.is_active),
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })

    assignments = []
    for row in ProviderPatient.query.all():
        if not row.provider or not row.patient:
            continue
        assignments.append({
            "provider": row.provider.username,
            "patient": row.patient.username,
        })
    return {"users": users, "assignments": assignments}


def restore_live_accounts(payload):
    from sqlalchemy import or_
    from app import db
    from app.models import ProviderPatient, User

    if not payload:
        return 0

    restored = 0
    for item in payload.get("users") or []:
        username = (item.get("username") or "").strip()
        email = (item.get("email") or "").strip().lower()
        if not username or username in DEMO_USERNAMES:
            continue
        existing = User.query.filter(or_(User.username == username, User.email == email)).first()
        if existing:
            continue
        created_at = None
        if item.get("created_at"):
            try:
                created_at = datetime.fromisoformat(item["created_at"])
            except ValueError:
                created_at = None
        password_hash = item.get("password_hash") or ""
        if not password_hash:
            continue
        db.session.add(User(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=item.get("full_name") or username,
            role=item.get("role") or "patient",
            professional_credentials=item.get("professional_credentials"),
            phone=item.get("phone"),
            address=item.get("address"),
            is_active=item.get("is_active", True),
            created_at=created_at or datetime.utcnow(),
        ))
        restored += 1

    db.session.flush()

    for item in payload.get("assignments") or []:
        provider = User.query.filter_by(username=item.get("provider")).first()
        patient = User.query.filter_by(username=item.get("patient")).first()
        if not provider or not patient:
            continue
        exists = ProviderPatient.query.filter_by(
            provider_id=provider.id, patient_id=patient.id
        ).first()
        if exists:
            continue
        db.session.add(ProviderPatient(provider_id=provider.id, patient_id=patient.id))
        restored += 1

    db.session.commit()
    return restored


def _fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "intelligent-diabetes-risk-predictor",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def load_backup_payload(app=None):
    urls = [
        f"https://raw.githubusercontent.com/{BACKUP_REPO}/{BACKUP_BRANCH}/{BACKUP_PATH}",
        f"https://raw.githubusercontent.com/{BACKUP_REPO}/main/{BACKUP_PATH}",
    ]
    for url in urls:
        try:
            payload = _fetch_json(url)
            if payload and (payload.get("users") or payload.get("assignments")):
                return payload
        except Exception:
            continue
    if app is not None:
        local_path = os.path.join(app.config["BASE_DIR"], *BACKUP_PATH.split("/"))
        if os.path.exists(local_path):
            try:
                with open(local_path, encoding="utf-8") as handle:
                    return json.load(handle)
            except Exception:
                return None
    return None


def restore_from_backup(app):
    try:
        payload = load_backup_payload(app)
        restored = restore_live_accounts(payload)
        if restored:
            print(f"Restored {restored} registered account(s) from live backup.")
    except Exception as exc:
        print(f"Live account restore skipped: {exc}")
