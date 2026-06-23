import re

from app import create_app
from app.models import HealthRecord, Prediction, User

app = create_app()

with app.app_context():
    client = app.test_client()
    user = User.query.filter_by(role="patient").first()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    page = client.get("/health-data")
    html = page.data.decode()
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    csrf = m.group(1) if m else ""

    cases = [
        ("healthy", 85, 22, 28),
        ("high", 190, 39, 55),
    ]
    before = Prediction.query.count()
    for label, g, b, a in cases:
        data = {
            "sex": "female",
            "pregnancies": "0",
            "glucose": str(g),
            "systolic": "120",
            "diastolic": "80",
            "skin_thickness": "20",
            "insulin": "80",
            "bmi": str(b),
            "diabetes_pedigree": "0",
            "age": str(a),
            "csrf_token": csrf,
        }
        resp = client.post("/health-data", data=data, follow_redirects=True)
        text = resp.data.decode()
        if "Please fix these issues" in text:
            import re as _re
            errs = _re.findall(r"<li>([^<]+)</li>", text)
            print("  validation errors:", errs[:5])
        pred = Prediction.query.order_by(Prediction.id.desc()).first()
        rec = HealthRecord.query.get(pred.health_record_id) if pred else None
        print(
            label,
            "status=", resp.status_code,
            "flash=", "Prediction complete" in text,
            "prob=", round(pred.probability * 100, 1) if pred else None,
            "g=", rec.glucose if rec else None,
            "bmi=", rec.bmi if rec else None,
        )
    print("predictions", before, "->", Prediction.query.count())
