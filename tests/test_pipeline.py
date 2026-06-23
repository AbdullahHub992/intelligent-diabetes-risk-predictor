import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from app.ml.pipeline import clean_data, train_all_models, FEATURE_COLUMNS, TARGET_COLUMN
from app.ml.validators import validate_dataset_columns


def test_dataset_validation():
    ok, _ = validate_dataset_columns(FEATURE_COLUMNS + [TARGET_COLUMN])
    assert ok
    bad, msg = validate_dataset_columns(["Glucose"])
    assert not bad
    assert "Missing" in msg


def test_clean_data():
    df = pd.DataFrame({
        "Pregnancies": [1, 2], "Glucose": [0, 120], "BloodPressure": [70, 80],
        "SkinThickness": [20, 25], "Insulin": [80, 90], "BMI": [25.0, 28.0],
        "DiabetesPedigreeFunction": [0.3, 0.4], "Age": [30, 40], "Outcome": [0, 1],
    })
    cleaned = clean_data(df)
    assert len(cleaned) == 2
    assert cleaned.iloc[0]["Glucose"] > 0


def test_train_models(tmp_path):
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "diabetes.csv"))
    results, best = train_all_models(df, str(tmp_path), test_size=0.3, random_state=42)
    assert len(results) == 4
    assert best in [r["model_name"] for r in results]
    assert os.path.exists(tmp_path / "scaler.joblib")
