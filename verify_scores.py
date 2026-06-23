"""Verify healthy vs high-risk inputs give different probabilities."""
import re

from app import create_app, db
from app.models import Prediction, User


def csrf(html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return m.group(1) if m else ""


def login_patient(client):
    r = client.get("/login/patient")
    return client.post(
        "/login/patient",
        data={
            "username": "patient",
            "password": "patient123",
            "csrf_token": csrf(r.data.decode()),
            "submit": "Login",
        },
        follow_redirects=True,
    )


def submit_health(client, glucose, bmi, age):
    r = client.get("/health-data")
    return client.post(
        "/health-data",
        data={
            "sex": "female",
            "pregnancies": "0",
            "glucose": str(glucose),
            "systolic": "120",
            "diastolic": "80",
            "skin_thickness": "20",
            "insulin": "80",
            "bmi": str(bmi),
            "diabetes_pedigree": "0",
            "age": str(age),
            "csrf_token": csrf(r.data.decode()),
            "submit": "Submit & Get Prediction",
        },
        follow_redirects=True,
    )


app = create_app()
client = app.test_client()

with app.app_context():
    login_patient(client)
    before = Prediction.query.count()
    for label, g, b, a in [("healthy", 85, 22, 25), ("high", 190, 39, 55)]:
        resp = submit_health(client, g, b, a)
        pred = Prediction.query.order_by(Prediction.id.desc()).first()
        print(
            f"{label}: {pred.probability * 100:.1f}% ({pred.risk_level}) "
            f"model={pred.model_name} saved={ 'Health data saved' in resp.data.decode() }"
        )
    print("new predictions:", Prediction.query.count() - before)
