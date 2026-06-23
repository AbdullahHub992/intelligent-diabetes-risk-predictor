import re

from app import create_app


def _csrf_token(client, url):
    response = client.get(url)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.data.decode())
    assert match, "CSRF token not found"
    return match.group(1)


def test_staff_login_requires_owner_code():
    app = create_app()
    client = app.test_client()
    token = _csrf_token(client, "/login/admin")
    response = client.post(
        "/login/admin",
        data={
            "username": "admin",
            "password": "admin123",
            "owner_access_code": "wrong-code",
            "csrf_token": token,
            "submit": "Login",
        },
        follow_redirects=True,
    )
    assert b"Invalid owner access code" in response.data


def test_staff_login_and_profile():
    app = create_app()
    client = app.test_client()
    token = _csrf_token(client, "/login/doctor")
    response = client.post(
        "/login/doctor",
        data={
            "username": "doctor",
            "password": "doctor123",
            "owner_access_code": "doctor2026",
            "csrf_token": token,
            "submit": "Login",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    profile = client.get("/profile")
    assert profile.status_code == 200
    assert b"Save Profile" in profile.data
