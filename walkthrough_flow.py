"""End-to-end walkthrough of SRS User Panel prediction flow."""
import re
import sys

from app import create_app
from app.models import Prediction, User


def csrf(html):
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        raise RuntimeError("CSRF token not found")
    return match.group(1)


def login(client, portal, username, password):
    r = client.get(f"/login/{portal}")
    data = {
        "username": username,
        "password": password,
        "csrf_token": csrf(r.data.decode()),
        "submit": "Login",
    }
    return client.post(f"/login/{portal}", data=data, follow_redirects=True)


def step(num, title, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"Step {num}: [{status}] {title}")
    if detail:
        print(f"         {detail}")
    return ok


def main():
    app = create_app()
    client = app.test_client()
    failures = []

    with app.app_context():
        patient_user = User.query.filter_by(username="patient").first()

        r = login(client, "user", "patient", "patient123")
        ok = r.status_code == 200 and b"Dashboard" in r.data
        if not step(1, "User (Patient) logs in", ok):
            failures.append("patient login")

        r = client.get("/health-data")
        html = r.data.decode()
        token = csrf(html)
        health_data = {
            "sex": "female",
            "pregnancies": "2",
            "glucose": "168",
            "systolic": "145",
            "diastolic": "92",
            "skin_thickness": "35",
            "insulin": "210",
            "bmi": "36.5",
            "diabetes_pedigree": "1",
            "age": "52",
            "smoking": "never",
            "physical_activity": "moderate",
            "diet_quality": "average",
            "csrf_token": token,
            "submit": "Generate Prediction",
        }
        r = client.post("/health-data", data=health_data, follow_redirects=True)
        prediction = (
            Prediction.query.filter_by(user_id=patient_user.id)
            .order_by(Prediction.created_at.desc())
            .first()
            if patient_user
            else None
        )
        ok = r.status_code == 200 and prediction is not None
        if not step(2, "Predict Risk generates a result", ok):
            failures.append("prediction")

        r = client.get("/dashboard")
        ok = r.status_code == 200 and (
            prediction.risk_level.encode() in r.data if prediction else False
        )
        if not step(3, "User Dashboard shows prediction", ok):
            failures.append("dashboard")

        r = client.get("/logout", follow_redirects=True)
        ok = r.status_code == 200
        if not step(4, "Logout", ok):
            failures.append("logout")

        r = login(client, "admin", "admin", "admin123")
        ok = r.status_code == 200 and b"Admin Panel" in r.data
        if not step(5, "Admin login", ok):
            failures.append("admin login")

        for path, label in [
            ("/admin/users", "Account Management"),
            ("/admin/upload-dataset", "Import Dataset"),
            ("/admin/eda", "EDA"),
            ("/admin/train-models", "Train Models"),
        ]:
            page = client.get(path)
            ok = page.status_code == 200
            if not step(6, f"Admin {label} accessible", ok):
                failures.append(label)

        r = client.get("/notifications")
        if not step(7, "Notifications URL is gone", r.status_code == 404):
            failures.append("notifications leftover")
        r = client.get("/send-report-to-admin")
        if not step(8, "Send Report to Admin URL is gone", r.status_code == 404):
            failures.append("send-report leftover")
        r = client.get("/admin/audit-logs")
        if not step(9, "Audit Logs URL is gone", r.status_code == 404):
            failures.append("audit leftover")
        r = client.get("/admin/received-reports")
        if not step(10, "Patient Reports inbox URL is gone", r.status_code == 404):
            failures.append("inbox leftover")
        r = client.get("/provider/forwarded-reports")
        if not step(11, "Forwarded reports URL is gone", r.status_code in (403, 404)):
            failures.append("forward leftover")

    if failures:
        print("FAILED:", ", ".join(failures))
        sys.exit(1)
    print("WALKTHROUGH OK")


if __name__ == "__main__":
    main()
