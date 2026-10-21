import re

from app import create_app, db
from app.models import User


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


def test_registration_emails_otp_before_creating_account(monkeypatch):
    sent = {}

    def fake_send(to_email, code, role_label):
        sent["to"] = to_email
        sent["code"] = code
        sent["role"] = role_label

    monkeypatch.setattr("app.routes.auth.send_registration_otp", fake_send)
    app = create_app()
    username = "otp-patient-check"
    _delete_user(app, username)
    client = app.test_client()
    try:
        token = _csrf_token(client, "/register")
        response = client.post(
            "/register",
            data={
                "csrf_token": token,
                "username": username,
                "full_name": "OTP Patient",
                "email": "otp-patient-check@gmail.com",
                "confirm_email": "otp-patient-check@gmail.com",
                "role": "patient",
                "password": "Patient1!x",
                "confirm_password": "Patient1!x",
                "submit": "Register",
            },
            follow_redirects=True,
        )
        page = response.data.decode()
        assert response.status_code == 200
        assert "Enter your code" in page
        assert sent["to"] == "otp-patient-check@gmail.com"
        assert sent["role"] == "patient"
        assert len(sent["code"]) == 6
        with app.app_context():
            assert User.query.filter_by(username=username).first() is None

        wrong = client.post(
            "/register/verify",
            data={"csrf_token": _csrf_token(client, "/register/verify"), "otp": "000000", "submit": "Verify"},
            follow_redirects=True,
        )
        assert b"That code is incorrect." in wrong.data
        with app.app_context():
            assert User.query.filter_by(username=username).first() is None

        verified = client.post(
            "/register/verify",
            data={
                "csrf_token": _csrf_token(client, "/register/verify"),
                "otp": sent["code"],
                "submit": "Verify and create account",
            },
            follow_redirects=True,
        )
        assert b"Email verified" in verified.data
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            assert user is not None
            assert user.role == "patient"
            assert user.check_password("Patient1!x")
    finally:
        _delete_user(app, username)


def test_provider_and_admin_registration_ask_for_emailed_code(monkeypatch):
    sent = []

    def fake_send(to_email, code, role_label):
        sent.append({"to": to_email, "code": code, "role": role_label})

    monkeypatch.setattr("app.routes.auth.send_registration_otp", fake_send)
    app = create_app()
    client = app.test_client()
    provider_name = "otp-provider-check"
    admin_name = "otp-admin-check"
    _delete_user(app, provider_name)
    _delete_user(app, admin_name)
    try:
        token = _csrf_token(client, "/register")
        provider = client.post(
            "/register",
            data={
                "csrf_token": token,
                "username": provider_name,
                "full_name": "OTP Provider",
                "email": "otp-provider-check@gmail.com",
                "confirm_email": "otp-provider-check@gmail.com",
                "role": "provider",
                "professional_credentials": "MD-99999",
                "password": "Doctor1!xy",
                "confirm_password": "Doctor1!xy",
                "submit": "Register",
            },
            follow_redirects=True,
        )
        assert b"healthcare provider" in provider.data
        assert sent[-1]["role"] == "healthcare provider"

        token = _csrf_token(client, "/register/admin")
        admin = client.post(
            "/register/admin",
            data={
                "csrf_token": token,
                "username": admin_name,
                "full_name": "OTP Admin",
                "email": "otp-admin-check@gmail.com",
                "confirm_email": "otp-admin-check@gmail.com",
                "password": "Admin123!",
                "confirm_password": "Admin123!",
                "access_code": "IDRP-ADMIN-01",
                "submit": "Register Admin",
            },
            follow_redirects=True,
        )
        assert b"administrator" in admin.data
        assert sent[-1]["role"] == "administrator"
        with app.app_context():
            assert User.query.filter_by(username=provider_name).first() is None
            assert User.query.filter_by(username=admin_name).first() is None
    finally:
        _delete_user(app, provider_name)
        _delete_user(app, admin_name)
