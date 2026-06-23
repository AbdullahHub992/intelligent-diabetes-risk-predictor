import json
import os

import joblib
import numpy as np

from app.ml.explainability import explain_prediction
from app.ml.pipeline import (
    MODEL_BUILDERS,
    get_best_model_name,
    load_model,
    load_production_pipeline,
    load_scaler,
    record_to_frame,
)
from app.ml.recommendations import generate_recommendation_plan
from app.utils import get_production_model_name

_model_cache = {}


def _risk_level(probability):
    if probability < 0.35:
        return "Low"
    if probability < 0.65:
        return "Moderate"
    return "High"


def _recommendations_json(risk_level, record, probability, explanation_json):
    plan = generate_recommendation_plan(record, probability, risk_level, explanation_json)
    return json.dumps(plan)


def _get_cached_pipeline(model_name, model_folder, *, production=False):
    key = f"{model_folder}:production" if production else f"{model_folder}:{model_name}"
    if key not in _model_cache:
        if production:
            _model_cache[key] = load_production_pipeline(model_folder)
        else:
            _model_cache[key] = load_model(model_name, model_folder)
    return _model_cache[key]


def clear_model_cache():
    _model_cache.clear()


def resolve_model_name(model_folder, model_name=None, *, for_patient=False):
    if for_patient:
        production = get_production_model_name()
        if production and production in MODEL_BUILDERS:
            return production
        return "Logistic Regression"
    if model_name:
        return model_name
    production = get_production_model_name()
    if production and production in MODEL_BUILDERS:
        return production
    return get_best_model_name(model_folder)


def _classifier_from_pipe(pipe):
    if hasattr(pipe, "named_steps") and "clf" in pipe.named_steps:
        return pipe.named_steps["clf"]
    return pipe


def predict_health_record(record, model_folder, model_name=None, *, for_patient=False):
    model_name = resolve_model_name(model_folder, model_name, for_patient=for_patient)

    if for_patient:
        pipe = _get_cached_pipeline(model_name, model_folder, production=True)
    else:
        pipe = _get_cached_pipeline(model_name, model_folder, production=False)

    if pipe is None:
        raise FileNotFoundError(
            "Models not trained yet. Run: python train_initial.py"
        )

    frame = record_to_frame(record)
    proba = float(pipe.predict_proba(frame)[0, 1])
    risk = _risk_level(proba)
    clf = _classifier_from_pipe(pipe)
    scaler = pipe.named_steps.get("scaler") if hasattr(pipe, "named_steps") else load_scaler(model_folder)
    explanation_json = explain_prediction(record, clf, scaler, model_name, proba, frame=frame)
    return {
        "model_name": model_name,
        "probability": proba,
        "risk_level": risk,
        "explanation": explanation_json,
        "recommendations": _recommendations_json(risk, record, proba, explanation_json),
        "recommendation_plan": generate_recommendation_plan(record, proba, risk, explanation_json),
    }
