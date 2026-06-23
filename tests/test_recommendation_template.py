from types import SimpleNamespace

from app import create_app
from app.ml.recommendations import generate_recommendation_plan


def test_recommendation_panel_renders():
    app = create_app()
    record = SimpleNamespace(
        pregnancies=1, glucose=120, bmi=28, systolic=120, diastolic=80,
        ml_blood_pressure=80, age=40, diabetes_pedigree=0, insulin=100,
        sex="female", skin_thickness=25,
    )
    plan = generate_recommendation_plan(record, 0.5, "Moderate")
    with app.test_request_context():
        from flask import render_template
        html = render_template("includes/recommendation_panel.html", recommendation_plan=plan)
    assert "Recommendation Summary" in html
    assert "&#10003;" in html or "✓" in html or "blood sugar" in html.lower()
