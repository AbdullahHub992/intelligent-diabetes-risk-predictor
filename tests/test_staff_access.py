import re

from app import create_app


def _csrf_token(client, url):
    response = client.get(url)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.data.decode())
    assert match, "CSRF token not found"
    return match.group(1)


def test_admin_login_with_credentials():
    app = create_app()
    client = app.test_client()
    token = _csrf_token(client, "/login/admin")
    response = client.post(
        "/login/admin",
        data={
            "username": "admin",
            "password": "admin123",
            "csrf_token": token,
            "submit": "Login",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Admin Panel" in response.data
    assert b"Owner Access Code" not in response.data


def test_admin_login_rejects_wrong_password():
    app = create_app()
    client = app.test_client()
    token = _csrf_token(client, "/login/admin")
    response = client.post(
        "/login/admin",
        data={
            "username": "admin",
            "password": "wrong-password",
            "csrf_token": token,
            "submit": "Login",
        },
        follow_redirects=True,
    )
    assert b"Invalid username/email or password" in response.data


def test_user_login_and_profile():
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

    profile = client.get("/profile")
    assert profile.status_code == 200
    assert b"Save Profile" in profile.data


def test_home_page_lists_srs_requirements():
    app = create_app()
    client = app.test_client()
    home = client.get("/")
    assert home.status_code == 200
    body = home.data
    assert b"FR-01" in body
    assert b"FR-20" in body
    assert b"Owner Access Code" not in body
    assert b"security question" not in body.lower()
    assert b"User Panel" in body
    assert b"Admin Panel" in body
