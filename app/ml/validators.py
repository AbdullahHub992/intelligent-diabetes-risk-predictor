from app.ml.pipeline import FEATURE_COLUMNS, TARGET_COLUMN


def validate_dataset_columns(columns):
    required = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    present = {c.strip() for c in columns}
    rename = {
        "Blood Pressure": "BloodPressure",
        "Skin Thickness": "SkinThickness",
        "Diabetes Pedigree Function": "DiabetesPedigreeFunction",
    }
    normalized = {rename.get(c, c) for c in present}
    missing = required - normalized
    if missing:
        return False, f"Missing required columns: {', '.join(sorted(missing))}"
    return True, "Dataset schema is valid."
