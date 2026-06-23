from app import create_app
from app.forms import HealthDataForm
from flask import request

app = create_app()

with app.test_request_context(
    "/health-data",
    method="POST",
    data={
        "sex": "female",
        "pregnancies": "0",
        "glucose": "85",
        "systolic": "120",
        "diastolic": "80",
        "skin_thickness": "20",
        "insulin": "80",
        "bmi": "22",
        "diabetes_pedigree": "0",
        "age": "28",
    },
):
    form = HealthDataForm()
    print("validate_on_submit", form.validate_on_submit())
    print("errors", form.errors)
    print("data", form.glucose.data, form.bmi.data)
