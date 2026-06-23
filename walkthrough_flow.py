"""End-to-end walkthrough: patient -> prediction -> admin -> doctor."""
import re
import sys

from app import create_app, db
from app.models import (
    AdminReportSubmission,
    DoctorReportForward,
    DoctorReportRemark,
    Prediction,
    User,
)
from app.utils import get_owner_access_code


def csrf(html):
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        raise RuntimeError("CSRF token not found")
    return match.group(1)


def login(client, portal, username, password, owner_code=None):
    r = client.get(f"/login/{portal}")
    data = {
        "username": username,
        "password": password,
        "csrf_token": csrf(r.data.decode()),
        "submit": "Login",
    }
    if owner_code is not None:
        data["owner_access_code"] = owner_code
    return client.post(f"/login/{portal}", data=data, follow_redirects=True)


def logout(client):
    return client.get("/logout", follow_redirects=True)


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
        admin_code = get_owner_access_code("admin")
        doctor_code = get_owner_access_code("doctor")
        patient_user = User.query.filter_by(username="patient").first()
        doctor_user = User.query.filter_by(username="doctor").first()

        # --- Step 1: Patient login ---
        r = login(client, "patient", "patient", "patient123")
        ok = r.status_code == 200 and b"Dashboard" in r.data
        if not step(1, "Patient logs in", ok):
            failures.append("patient login")

        # --- Step 2: Submit health data ---
        r = client.get("/health-data")
        html = r.data.decode()
        token = csrf(html)
        # Elevated values for a clear diabetes risk signal
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
            "model_choice": "",
            "csrf_token": token,
            "submit": "Submit & Get Prediction",
        }
        r = client.post("/health-data", data=health_data, follow_redirects=True)
        html = r.data.decode()
        has_prediction = (
            b"probability" in r.data.lower()
            or b"risk" in r.data.lower()
            or b"Health data saved" in r.data
        )
        if not step(2, "Patient submits health data", has_prediction, "Form submitted with elevated glucose/BMI"):
            failures.append("health data submit")

        prediction = (
            Prediction.query.filter_by(user_id=patient_user.id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        ok = prediction is not None
        detail = ""
        if prediction:
            detail = (
                f"Risk: {prediction.risk_level} | "
                f"Probability: {prediction.probability:.1%} | "
                f"Model: {prediction.model_name}"
            )
        if not step(3, "System generates ML prediction", ok, detail):
            failures.append("prediction")

        # --- Step 4: Patient dashboard shows result ---
        r = client.get("/dashboard")
        ok = r.status_code == 200 and (
            prediction.risk_level.encode() in r.data
            if prediction
            else False
        )
        if not step(4, "Patient dashboard shows prediction", ok):
            failures.append("patient dashboard")

        # --- Step 5: Send report to admin ---
        r = client.get("/send-report-to-admin")
        ok = r.status_code == 200 and b"Send Report to Admin" in r.data
        if not step(5, "Patient opens Send to Admin page", ok):
            failures.append("send report page")

        token = csrf(r.data.decode())
        r = client.post(
            "/send-report-to-admin",
            data={
                "prediction_id": str(prediction.id),
                "message": "Walkthrough test: please review my elevated risk results.",
                "csrf_token": token,
                "submit": "Send Report to Admin",
            },
            follow_redirects=True,
        )
        submission = (
            AdminReportSubmission.query.filter_by(
                patient_id=patient_user.id,
                prediction_id=prediction.id,
            )
            .order_by(AdminReportSubmission.created_at.desc())
            .first()
        )
        ok = submission is not None and b"sent to the admin" in r.data.lower()
        if not step(
            6,
            "Patient sends report to admin",
            ok,
            f"Report ID: {submission.id if submission else 'none'}",
        ):
            failures.append("send to admin")

        logout(client)

        # --- Step 7: Admin sees report ---
        r = login(client, "admin", "admin", "admin123", admin_code)
        ok = r.status_code == 200
        if not step(7, "Admin logs in", ok):
            failures.append("admin login")

        r = client.get("/admin/received-reports")
        ok = (
            r.status_code == 200
            and submission
            and str(submission.id).encode() in r.data
            or (submission and patient_user.full_name.encode() in r.data)
        )
        if not step(8, "Admin sees report in inbox", ok):
            failures.append("admin inbox")

        r = client.get(f"/admin/received-reports/{submission.id}")
        ok = r.status_code == 200 and b"Walkthrough test" in r.data
        if not step(9, "Admin opens report detail", ok):
            failures.append("admin report detail")

        # --- Step 10: Admin forwards to doctor ---
        r = client.get(f"/admin/received-reports/{submission.id}")
        token = csrf(r.data.decode())
        r = client.post(
            f"/admin/received-reports/{submission.id}",
            data={
                "provider_ids": str(doctor_user.id),
                "admin_note": "Walkthrough: please review this patient case.",
                "csrf_token": token,
                "submit": "Send Report to Selected Doctors",
            },
            follow_redirects=True,
        )
        forward = DoctorReportForward.query.filter_by(
            admin_report_id=submission.id,
            provider_id=doctor_user.id,
        ).first()
        ok = forward is not None and b"sent to" in r.data.lower()
        if not step(
            10,
            "Admin forwards report to doctor",
            ok,
            f"Forward ID: {forward.id if forward else 'none'}",
        ):
            failures.append("admin forward")

        logout(client)

        # --- Step 11: Doctor sees forwarded report ---
        r = login(client, "doctor", "doctor", "doctor123", doctor_code)
        ok = r.status_code == 200
        if not step(11, "Doctor logs in", ok):
            failures.append("doctor login")

        r = client.get("/provider/forwarded-reports")
        ok = r.status_code == 200 and forward and str(forward.id).encode() in r.data
        if not step(12, "Doctor sees forwarded report in inbox", ok):
            failures.append("doctor inbox")

        r = client.get(f"/provider/forwarded-reports/{forward.id}")
        ok = (
            r.status_code == 200
            and b"Walkthrough" in r.data
            and prediction.risk_level.encode() in r.data
        )
        if not step(13, "Doctor opens report and sees patient risk data", ok):
            failures.append("doctor report detail")

        # --- Step 14: Doctor views assigned patient ---
        r = client.get(f"/provider/patient/{patient_user.id}")
        ok = r.status_code == 200 and patient_user.full_name.encode() in r.data
        if not step(14, "Doctor views assigned patient profile", ok):
            failures.append("doctor patient view")

        # --- Step 15: Doctor sends remark to patient ---
        r = client.get(f"/provider/forwarded-reports/{forward.id}")
        token = csrf(r.data.decode())
        r = client.post(
            f"/provider/forwarded-reports/{forward.id}",
            data={
                "form_type": "remark",
                "remark": "Walkthrough: please schedule a follow-up glucose test within 2 weeks.",
                "csrf_token": token,
                "submit": "Send Remark to Patient",
            },
            follow_redirects=True,
        )
        remark = (
            DoctorReportRemark.query.filter_by(
                patient_id=patient_user.id,
                provider_id=doctor_user.id,
                prediction_id=prediction.id,
            )
            .order_by(DoctorReportRemark.created_at.desc())
            .first()
        )
        ok = remark is not None and b"Remark sent" in r.data
        if not step(15, "Doctor sends remark to patient", ok):
            failures.append("doctor remark")

        logout(client)

        # --- Step 16: Patient sees doctor notification ---
        r = login(client, "patient", "patient", "patient123")
        r = client.get("/notifications")
        ok = (
            r.status_code == 200
            and remark
            and b"follow-up glucose test" in r.data
        )
        if not step(16, "Patient sees doctor notification/remark", ok):
            failures.append("patient notification")

        print("=" * 60)
        if failures:
            print(f"WALKTHROUGH FAILED ({len(failures)} step(s)): {', '.join(failures)}")
            sys.exit(1)
        print("FULL WALKTHROUGH PASSED — all 16 steps completed successfully")
        print("=" * 60)


if __name__ == "__main__":
    main()
