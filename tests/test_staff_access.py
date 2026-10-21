import re

from app import create_app


def _csrf_token(client, url):
    response = client.get(url)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.data.decode())
    assert match, "CSRF token not found"
    return match.group(1)


def test_seeded_admin_login_is_removed():
    app = create_app()
    client = app.test_client()
    token = _csrf_token(client, "/login/admin")
    response = client.post(
        "/login/admin",
        data={
            "username": "admin",
            "password": "admin123",
            "access_code": "IDRP-ADMIN-01",
            "csrf_token": token,
            "submit": "Login",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username/email or password" in response.data
    assert b"Admin Panel" not in response.data


def test_admin_login_accepts_any_one_of_three_access_codes():
    from app import db
    from app.models import User

    app = create_app()
    username = "otp-admin-code-check"
    with app.app_context():
        existing = User.query.filter_by(username=username).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
        user = User(
            username=username,
            email="otp-admin-code-check@gmail.com",
            full_name="Code Admin",
            role="admin",
            is_active=True,
        )
        user.set_password("AdminPass1!")
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    try:
        token = _csrf_token(client, "/login/admin")
        rejected = client.post(
            "/login/admin",
            data={
                "username": username,
                "password": "AdminPass1!",
                "access_code": "not-a-real-code",
                "csrf_token": token,
                "submit": "Login",
            },
            follow_redirects=True,
        )
        assert b"That access code is not valid" in rejected.data

        token = _csrf_token(client, "/login/admin")
        accepted = client.post(
            "/login/admin",
            data={
                "username": username,
                "password": "AdminPass1!",
                "access_code": "IDRP-ADMIN-02",
                "csrf_token": token,
                "submit": "Login",
            },
            follow_redirects=True,
        )
        assert b"Admin Panel" in accepted.data
    finally:
        with app.app_context():
            from app.models import AuditLog
            user = User.query.filter_by(username=username).first()
            if user:
                AuditLog.query.filter_by(user_id=user.id).delete(synchronize_session=False)
                db.session.delete(user)
                db.session.commit()


def test_admin_login_rejects_wrong_password():
    app = create_app()
    client = app.test_client()
    token = _csrf_token(client, "/login/admin")
    response = client.post(
        "/login/admin",
        data={
            "username": "admin",
            "password": "wrong-password",
            "access_code": "IDRP-ADMIN-01",
            "csrf_token": token,
            "submit": "Login",
        },
        follow_redirects=True,
    )
    assert b"Invalid username/email or password" in response.data


def test_seeded_doctor_login_is_removed():
    app = create_app()
    client = app.test_client()
    token = _csrf_token(client, "/login/user")
    response = client.post(
        "/login/user",
        data={
            "username": "doctor",
            "password": "doctor123",
            "csrf_token": token,
            "submit": "Login",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username/email or password" in response.data


def test_home_page_lists_panels_without_fr_labels():
    app = create_app()
    client = app.test_client()
    home = client.get("/")
    assert home.status_code == 200
    body = home.data
    assert b"FR-01" not in body
    assert b"FR-20" not in body
    assert b"Owner Access Code" not in body
    assert b"security question" not in body.lower()
    assert b"User Panel" in body
    assert b"Admin Panel" in body
