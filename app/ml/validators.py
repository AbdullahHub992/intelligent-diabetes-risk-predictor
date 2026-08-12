from app.ml.pipeline import FEATURE_COLUMNS, TARGET_COLUMN


def validate_dataset_columns(columns):
    required = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    present = {c.strip() for c in columns}
    rename = {
        "Blood Pressure": "BloodPressure",
        "Skin Thickness": "SkinThickness",
        "Diabetes Pedigree Function": "DiabetesPedigreeFunction",
        "DiabetesPedigree": "DiabetesPedigreeFunction",
        "BP": "BloodPressure",
        "bloodpressure": "BloodPressure",
        "glucose": "Glucose",
        "bmi": "BMI",
        "age": "Age",
        "outcome": "Outcome",
        "pregnancies": "Pregnancies",
        "insulin": "Insulin",
        "skinthickness": "SkinThickness",
    }
    normalized = set()
    for c in present:
        key = rename.get(c, rename.get(c.lower(), c))
        normalized.add(key)
    missing = required - normalized
    if missing:
        return False, f"Missing required columns: {', '.join(sorted(missing))}"
    return True, "Dataset schema is valid."
