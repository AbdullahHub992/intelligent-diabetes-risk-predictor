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


def test_forgot_password_requires_emailed_code(monkeypatch):
    sent = {}

    def fake_send(to_email, code):
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
