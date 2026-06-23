"""Quick check: web form predictions should vary and use Logistic Regression."""
import re

from app import create_app, db
from app.models import Prediction, User

app = create_app()


def login_patient(client):
    with app.app_context():
        user = User.query.filter_by(role="patient").first()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True


def post_health(client, glucose, bmi, age):
    page = client.get("/health-data")
    data = {
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
        "submit": "Submit & Get Prediction",
    }
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page.data.decode())
    if m:
        data["csrf_token"] = m.group(1)
    return client.post("/health-data", data=data, follow_redirects=True)


with app.app_context():
    client = app.test_client()
    login_patient(client)
    before = Prediction.query.count()
    for label, g, b, a in [("healthy", 85, 22, 25), ("default", 95, 25, 33), ("high", 190, 39, 55)]:
        resp = post_health(client, g, b, a)
        text = resp.data.decode()
        m = re.search(r"display-4[^>]*>\s*([\d.]+)%", text)
        pred = Prediction.query.order_by(Prediction.id.desc()).first()
        print(
            label,
            "status=", resp.status_code,
            "page_pct=", m.group(1) if m else "NONE",
            "db_prob=", round(pred.probability * 100, 1) if pred else "?",
            "model=", pred.model_name if pred else "?",
            "flash=", "Health data saved" in text,
        )
    after = Prediction.query.count()
    print("predictions before", before, "after", after)
