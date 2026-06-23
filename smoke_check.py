"""Quick smoke test for all major website routes and assets."""
import os
import re
import sys
from types import SimpleNamespace

from app import create_app
from app.ml.predictor import predict_health_record
from app.utils import get_owner_access_code, verify_owner_access_code

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_FOLDER = os.path.join(ROOT, "saved_models")
STATIC = os.path.join(ROOT, "app", "static")
MODELS = os.path.join(ROOT, "saved_models")
DATA = os.path.join(ROOT, "data", "diabetes.csv")
DB = os.path.join(ROOT, "instance", "diabetes.db")

issues = []
checks = []


def ok(msg):
    checks.append(f"OK  {msg}")


def fail(msg):
    issues.append(msg)


def csrf_token(client, url):
    response = client.get(url)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.data.decode())
    return match.group(1) if match else None


def login(client, portal, username, password, owner_code=None):
    path = f"/login/{portal}"
    token = csrf_token(client, path)
    if not token:
        return None, "CSRF token missing"
    data = {
        "username": username,
        "password": password,
        "csrf_token": token,
        "submit": "Login",
    }
    if owner_code is not None:
        data["owner_access_code"] = owner_code
    return client.post(path, data=data, follow_redirects=True), None


def main():
    # Files on disk
    required_files = [
        (DB, "Database"),
        (DATA, "Dataset"),
        (os.path.join(STATIC, "css", "style.css"), "CSS"),
        (os.path.join(STATIC, "images", "hero-medical-bg.png"), "Hero background image"),
        (os.path.join(MODELS, "best_model.joblib"), "Best ML model"),
        (os.path.join(MODELS, "scaler.joblib"), "Scaler"),
        (os.path.join(STATIC, "plots", "model_comparison.png"), "Model comparison plot"),
    ]
    for path, label in required_files:
        if os.path.isfile(path):
            ok(f"{label} exists")
        else:
            fail(f"Missing: {label} ({path})")

    app = create_app()
    client = app.test_client()

    with app.app_context():
        admin_code = get_owner_access_code("admin")
        doctor_code = get_owner_access_code("doctor")
        if admin_code and doctor_code:
            ok(f"Owner codes configured (admin/doctor)")
        else:
            fail("Owner access codes not set in database")

        if verify_owner_access_code("admin", admin_code or ""):
            ok("Admin code verification works")
        else:
            fail("Admin code verification failed")

    # Public pages
    public_routes = [
        ("/", "Home page"),
        ("/login/patient", "Patient login"),
        ("/login/doctor", "Doctor login"),
        ("/login/admin", "Admin login"),
        ("/register", "Register page"),
    ]
    for path, label in public_routes:
        r = client.get(path)
        if r.status_code == 200:
            ok(f"{label} loads ({path})")
        else:
            fail(f"{label} returned {r.status_code} ({path})")

    home = client.get("/")
    home_html = home.data.decode()
    if "hero-medical-bg.png" in home_html or "home-hero" in home_html:
        ok("Home page has medical hero section")
    else:
        fail("Home page missing hero background markup")

    css = client.get("/static/css/style.css")
    if css.status_code == 200 and b"home-hero" in css.data:
        ok("Home hero CSS served")
    else:
        fail("Home hero CSS not loading correctly")

    img = client.get("/static/images/hero-medical-bg.png")
    if img.status_code == 200 and len(img.data) > 10000:
        ok(f"Hero image served ({len(img.data) // 1024} KB)")
    else:
        fail("Hero background image not served")

    # Patient login + dashboard
    r, err = login(client, "patient", "patient", "patient123")
    if err:
        fail(f"Patient login: {err}")
    elif r.status_code == 200 and (b"Dashboard" in r.data or b"dashboard" in r.data.lower()):
        ok("Patient login works")
    else:
        fail("Patient login failed or dashboard not reached")

    for path, label, allow_redirect in [
        ("/dashboard", "Patient dashboard", False),
        ("/health-data", "Health data form", False),
        ("/my-health-records", "Health records", False),
        ("/progress", "Progress page", False),
        ("/education", "Education page", False),
        ("/send-report-to-admin", "Send to admin", True),
        ("/feedback", "Feedback page", False),
        ("/notifications", "Notifications page", False),
    ]:
        r = client.get(path)
        if r.status_code == 200:
            ok(f"{label} accessible")
        elif r.status_code == 302 and allow_redirect:
            ok(f"{label} redirects when no data yet (expected)")
        elif r.status_code == 302:
            fail(f"{label} redirected unexpectedly ({path})")
        else:
            fail(f"{label} returned {r.status_code} ({path})")

    client.get("/logout", follow_redirects=True)

    # Admin login + pages
    r, err = login(client, "admin", "admin", "admin123", admin_code)
    if err:
        fail(f"Admin login: {err}")
    elif r.status_code == 200:
        ok("Admin login works")
    else:
        fail("Admin login failed")

    for path, label in [
        ("/admin/", "Admin dashboard"),
        ("/admin/users", "User management"),
        ("/admin/assignments", "Doctor assignments"),
        ("/admin/upload-dataset", "Dataset upload"),
        ("/admin/eda", "EDA page"),
        ("/admin/train-models", "Train models"),
        ("/admin/received-reports", "Received reports"),
        ("/profile", "Admin profile"),
    ]:
        r = client.get(path)
        if r.status_code == 200:
            ok(f"{label} accessible")
        else:
            fail(f"{label} returned {r.status_code} ({path})")

    client.get("/logout", follow_redirects=True)

    # Doctor login + pages
    r, err = login(client, "doctor", "doctor", "doctor123", doctor_code)
    if err:
        fail(f"Doctor login: {err}")
    elif r.status_code == 200:
        ok("Doctor login works")
    else:
        fail("Doctor login failed")

    for path, label in [
        ("/provider/", "Doctor dashboard"),
        ("/provider/forwarded-reports", "Forwarded reports"),
        ("/profile", "Doctor profile"),
    ]:
        r = client.get(path)
        if r.status_code == 200:
            ok(f"{label} accessible")
        else:
            fail(f"{label} returned {r.status_code} ({path})")

    # ML prediction smoke test
    sample = SimpleNamespace(
        sex="female",
        pregnancies=1,
        glucose=120,
        ml_blood_pressure=70,
        skin_thickness=20,
        insulin=80,
        bmi=28.5,
        diabetes_pedigree=0.35,
        age=35,
    )
    try:
        with app.app_context():
            result = predict_health_record(sample, MODEL_FOLDER)
        if result and "risk_level" in result and "probability" in result:
            ok(f"ML prediction works (risk: {result['risk_level']})")
        else:
            fail("ML prediction returned incomplete result")
    except Exception as exc:
        fail(f"ML prediction error: {exc}")

    # Bad login should fail
    client.get("/logout", follow_redirects=True)
    r, _ = login(client, "admin", "admin", "admin123", "wrong-code")
    if b"Invalid owner access code" in r.data or b"access code" in r.data.lower():
        ok("Invalid admin code correctly rejected")
    else:
        fail("Invalid admin code was not rejected")

    print("=" * 60)
    print("WEBSITE SMOKE CHECK")
    print("=" * 60)
    for line in checks:
        print(line)
    if issues:
        print("-" * 60)
        print(f"ISSUES ({len(issues)}):")
        for issue in issues:
            print(f"  X  {issue}")
        print("=" * 60)
        sys.exit(1)
    print("-" * 60)
    print(f"All checks passed ({len(checks)} total)")
    print("=" * 60)


if __name__ == "__main__":
    main()
