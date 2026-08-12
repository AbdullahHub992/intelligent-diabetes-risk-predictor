import json

import numpy as np

from app.ml.pipeline import FEATURE_COLUMNS, load_model, record_to_frame


FEATURE_LABELS = {
    "Pregnancies": "Pregnancies",
    "Glucose": "Glucose",
    "BloodPressure": "Blood Pressure",
    "SkinThickness": "Skin Thickness",
    "Insulin": "Insulin Level",
    "BMI": "BMI",
    "DiabetesPedigreeFunction": "Diabetes Pedigree",
    "Age": "Age",
    "Systolic": "Systolic Blood Pressure",
}

CLINICAL_THRESHOLDS = {
    "Glucose": (140, "High blood glucose is a major diabetes risk factor."),
    "BMI": (30, "Elevated BMI indicates obesity-related risk."),
    "BloodPressure": (90, "High diastolic blood pressure correlates with diabetes risk."),
    "Systolic": (140, "High systolic blood pressure increases cardiovascular and diabetes risk."),
    "Age": (45, "Age above 45 increases diabetes susceptibility."),
    "Insulin": (200, "High insulin levels may indicate insulin resistance."),
    "DiabetesPedigreeFunction": (1, "Family history of diabetes increases your risk."),
    "Pregnancies": (3, "Multiple pregnancies may increase gestational diabetes history."),
    "SkinThickness": (35, "Elevated skin fold thickness may indicate adiposity."),
}


def get_feature_importance(model, scaled_features):
    importances = []
    if hasattr(model, "feature_importances_"):
        for col, val in zip(FEATURE_COLUMNS, model.feature_importances_):
            importances.append({"feature": FEATURE_LABELS[col], "importance": float(val)})
    elif hasattr(model, "coef_"):
        coefs = np.abs(model.coef_[0])
        for col, val in zip(FEATURE_COLUMNS, coefs):
            importances.append({"feature": FEATURE_LABELS[col], "importance": float(val)})
    importances.sort(key=lambda x: x["importance"], reverse=True)
    return importances[:5]


def explain_prediction(record, model, scaler, model_name, probability, frame=None):
    frame = frame if frame is not None else record_to_frame(record)
    if hasattr(scaler, "named_steps") or frame is None:
        scaled = frame  # pipeline path uses frame directly for importance only
    else:
        scaled = scaler.transform(frame)
    factors = []

    importances = get_feature_importance(model, scaled)
    for item in importances[:3]:
        factors.append({
            "factor": item["feature"],
            "value": round(item["importance"], 4),
            "message": f"Model ({model_name}) identified this as a key contributing feature.",
            "type": "ml_importance",
        })

    value_map = {
        "Glucose": record.glucose,
        "BMI": record.bmi,
        "BloodPressure": record.ml_blood_pressure,
        "Systolic": getattr(record, "systolic", None) or 0,
        "Age": record.age,
        "Insulin": record.insulin,
        "DiabetesPedigreeFunction": record.diabetes_pedigree,
        "Pregnancies": record.pregnancies,
        "SkinThickness": record.skin_thickness,
    }
    for col, (threshold, message) in CLINICAL_THRESHOLDS.items():
        if value_map[col] >= threshold:
            factors.append({
                "factor": FEATURE_LABELS.get(col, col),
                "value": value_map[col],
                "message": message,
                "type": "clinical_threshold",
            })

    if not factors:
        factors.append({
            "factor": "Overall Profile",
            "value": round(probability, 4),
            "message": "Combined feature profile contributes to the assessed risk level.",
            "type": "general",
        })

    return json.dumps(factors)
