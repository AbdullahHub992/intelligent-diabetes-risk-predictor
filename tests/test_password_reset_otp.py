import re

from app import create_app, db
from app.models import User
from app.routes.auth import _mask_email


def _csrf_token(client, url):
    response = client.get(url)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.data.decode())
    assert match, "CSRF token not found"
    return match.group(1)


def _delete_user(app, username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()


def test_forgot_password_requires_emailed_code(monkeypatch):
    sent = {}

    def fake_send(to_email, code, role_label="account"):
        sent["to"] = to_email
        sent["code"] = code

    monkeypatch.setattr("app.routes.auth.send_password_reset_otp", fake_send)
    app = create_app()
    username = "otp-reset-check"
    _delete_user(app, username)
    with app.app_context():
        user = User(
            username=username,
            email="otp-reset-check@gmail.com",
            full_name="Reset Check",
            role="patient",
            is_active=True,
        )
        user.set_password("OldPass1!x")
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    try:
        token = _csrf_token(client, "/forgot-password")
        started = client.post(
            "/forgot-password",
            data={"csrf_token": token, "login": username, "submit": "Continue"},
            follow_redirects=True,
        )
        page = started.data.decode()
        assert "Enter it here before choosing a new password" in page
        assert sent["to"] == "otp-reset-check@gmail.com"
        assert len(sent["code"]) == 6
        with app.app_context():
            assert User.query.filter_by(username=username).first().check_password("OldPass1!x")

        wrong = client.post(
            "/forgot-password",
            data={"csrf_token": _csrf_token(client, "/forgot-password"), "otp": "000000"},
        )
        assert b"That code is incorrect." in wrong.data
        with app.app_context():
            assert User.query.filter_by(username=username).first().check_password("OldPass1!x")

        verified = client.post(
            "/forgot-password",
            data={"csrf_token": _csrf_token(client, "/forgot-password"), "otp": sent["code"]},
        )
        assert b"Choose a new password" in verified.data

        reset = client.post(
            "/forgot-password",
            data={
                "csrf_token": _csrf_token(client, "/forgot-password"),
                "new_password": "NewPass2!y",
                "confirm_password": "NewPass2!y",
                "submit": "Reset Password",
            },
            follow_redirects=True,
        )
        assert b"Password reset successful" in reset.data
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            assert user.check_password("NewPass2!y")
            assert not user.check_password("OldPass1!x")
    finally:
        _delete_user(app, username)


def test_user_and_admin_password_resets_stay_separate(monkeypatch):
    sent = []

    def fake_send(to_email, code, role_label="account"):
        sent.append({"to": to_email, "code": code, "role": role_label})

    monkeypatch.setattr("app.routes.auth.send_password_reset_otp", fake_send)
    app = create_app()
    patient_name = "otp-reset-patient"
    admin_name = "otp-reset-admin"
    _delete_user(app, patient_name)
    _delete_user(app, admin_name)
    with app.app_context():
        patient = User(
            username=patient_name,
            email="otp-reset-patient@gmail.com",
            full_name="Reset Patient",
            role="patient",
            is_active=True,
        )
        patient.set_password("OldPass1!x")
        admin = User(
            username=admin_name,
            email="otp-reset-admin@gmail.com",
            full_name="Reset Admin",
            role="admin",
            is_active=True,
        )
        admin.set_password("AdminPass1!")
        db.session.add_all([patient, admin])
        db.session.commit()

    client = app.test_client()
    try:
        token = _csrf_token(client, "/forgot-password/user")
        started = client.post(
            "/forgot-password/user",
            data={"csrf_token": token, "login": patient_name, "submit": "Continue"},
            follow_redirects=True,
        )
        assert b"otp-reset-patient@gmail.com" not in started.data
        assert b"Enter it here before choosing a new password" in started.data
        assert sent[-1]["role"] == "patient"

        admin_page = client.get("/forgot-password/admin")
        admin_body = admin_page.data.decode()
        assert "Enter the admin username or email" in admin_body
        assert "Enter it here before choosing a new password" not in admin_body

        wrong_portal = client.post(
            "/forgot-password/admin",
            data={
                "csrf_token": _csrf_token(client, "/forgot-password/admin"),
                "login": patient_name,
                "submit": "Continue",
            },
            follow_redirects=True,
        )
        assert b"Use Forgot password on the User login page." in wrong_portal.data
        assert [item["role"] for item in sent] == ["patient"]

        admin_started = client.post(
            "/forgot-password/admin",
            data={
                "csrf_token": _csrf_token(client, "/forgot-password/admin"),
                "login": admin_name,
                "submit": "Continue",
            },
            follow_redirects=True,
        )
        assert b"Enter it here before choosing a new password" in admin_started.data
        assert sent[-1]["to"] == "otp-reset-admin@gmail.com"
        assert sent[-1]["role"] == "administrator"

        user_page = client.get("/forgot-password/user").data.decode()
        assert _mask_email("otp-reset-patient@gmail.com") in user_page
        assert _mask_email("otp-reset-admin@gmail.com") not in user_page
    finally:
        _delete_user(app, patient_name)
        _delete_user(app, admin_name)
