import os
from datetime import datetime

import pandas as pd

from app import db
from app.ml.pipeline import FEATURE_COLUMNS, TARGET_COLUMN, clean_data, load_dataset, train_all_models
from app.models import Dataset, Feedback, HealthRecord, ModelMetrics, Prediction, TrainingJob


def build_feedback_training_rows():
    rows = []
    feedbacks = Feedback.query.filter(
        Feedback.actual_outcome.isnot(None),
        Feedback.used_in_training == False,
    ).all()
    for fb in feedbacks:
        if not fb.prediction_id:
            continue
        prediction = Prediction.query.get(fb.prediction_id)
        if not prediction:
            continue
        record = HealthRecord.query.get(prediction.health_record_id)
        if not record:
            continue
        rows.append({
            "Pregnancies": record.pregnancies,
            "Glucose": record.glucose,
            "BloodPressure": record.ml_blood_pressure,
            "SkinThickness": record.skin_thickness,
            "Insulin": record.insulin,
            "BMI": record.bmi,
            "DiabetesPedigreeFunction": record.diabetes_pedigree,
            "Age": record.age,
            "Outcome": fb.actual_outcome,
            "_feedback_id": fb.id,
        })
    return rows


def retrain_with_feedback(model_folder, upload_folder, test_size=0.3, random_state=42):
    active = Dataset.query.filter_by(is_active=True).first()
    if not active:
        raise FileNotFoundError("No active dataset found.")

    filepath = os.path.join(upload_folder, active.filename)
    base_df = clean_data(load_dataset(filepath))
    feedback_rows = build_feedback_training_rows()

    job = TrainingJob(
        job_type="feedback_retrain",
        dataset_filename=active.filename,
        rows_used=len(base_df),
        feedback_rows=len(feedback_rows),
        status="running",
    )
    db.session.add(job)
    db.session.flush()

    if feedback_rows:
        feedback_df = pd.DataFrame(feedback_rows).drop(columns=["_feedback_id"])
        combined = pd.concat([base_df, feedback_df], ignore_index=True)
        for row in feedback_rows:
            fb = Feedback.query.get(row["_feedback_id"])
            if fb:
                fb.used_in_training = True
    else:
        combined = base_df

    results, best_model = train_all_models(
        combined, model_folder, test_size=test_size, random_state=random_state,
    )

    ModelMetrics.query.delete()
    for r in results:
        db.session.add(ModelMetrics(
            model_name=r["model_name"],
            accuracy=r["accuracy"],
            precision=r["precision"],
            recall=r["recall"],
            f1_score=r["f1_score"],
            confusion_matrix=__import__("json").dumps(r["confusion_matrix"]),
            confusion_matrix_plot=r.get("confusion_matrix_plot"),
            is_best=r["is_best"],
            training_job_id=job.id,
        ))

    job.best_model = best_model
    job.rows_used = len(combined)
    job.status = "completed"
    job.completed_at = datetime.utcnow()
    db.session.commit()
    return results, best_model, len(feedback_rows)
