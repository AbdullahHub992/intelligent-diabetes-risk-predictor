from app import create_app, db
from app.models import HealthRecord, Prediction
from app.ml.predictor import predict_health_record, clear_model_cache

app = create_app()

with app.app_context():
    clear_model_cache()
    folder = app.config["MODEL_FOLDER"]

    print("=== Recent DB predictions ===")
    for p in Prediction.query.order_by(Prediction.id.desc()).limit(10).all():
        r = HealthRecord.query.get(p.health_record_id)
        print(
            f"id={p.id} prob={p.probability * 100:.1f}% model={p.model_name} "
            f"g={r.glucose} bmi={r.bmi} age={r.age} ins={r.insulin}"
        )

    def mk(**kw):
        d = dict(
            user_id=1, sex="female", pregnancies=0, glucose=95,
            systolic=120, diastolic=80, skin_thickness=20, insulin=80,
            bmi=25, diabetes_pedigree=0.28, age=33,
        )
        d.update(kw)
        return HealthRecord(**d)

    cases = [
        ("very healthy", mk(glucose=70, bmi=20, age=22)),
        ("healthy", mk(glucose=85, bmi=22, age=25)),
        ("normal", mk(glucose=100, bmi=24, age=35)),
        ("defaults", mk()),
        ("pre-diabetic", mk(glucose=125, bmi=29, age=45)),
        ("high", mk(glucose=160, bmi=34, age=50, diabetes_pedigree=0.65)),
        ("very high", mk(glucose=200, bmi=40, age=60, insulin=300, diabetes_pedigree=0.65)),
        ("insulin=0", mk(glucose=85, bmi=22, insulin=0)),
    ]
    print("\n=== Live model (Logistic Regression) ===")
    for name, rec in cases:
        out = predict_health_record(rec, folder, for_patient=True)
        pct = out["probability"] * 100
        print(f"{name:14} {pct:6.1f}%  {out['risk_level']}")
