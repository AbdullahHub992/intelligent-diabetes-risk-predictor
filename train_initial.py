"""Initial setup: register dataset, train all ML models, save artifacts."""
import json
import os

from app import create_app, db
from app.ml.pipeline import MODEL_BUILDERS, clean_data, generate_eda, load_dataset, train_all_models
from app.models import Dataset, ModelMetrics, TrainingJob
from app.utils import set_production_model_name
from datetime import datetime

app = create_app()

with app.app_context():
    data_path = os.path.join(app.config["UPLOAD_FOLDER"], "diabetes.csv")
    if not os.path.exists(data_path):
        print("ERROR: data/diabetes.csv not found. Run: python setup_data.py")
        exit(1)

    df = clean_data(load_dataset(data_path))
    generate_eda(df, app.config["PLOT_FOLDER"])

    if not Dataset.query.filter_by(filename="diabetes.csv").first():
        Dataset.query.update({Dataset.is_active: False})
        db.session.add(Dataset(filename="diabetes.csv", rows=len(df), uploaded_by=1, is_active=True))
        db.session.commit()

    job = TrainingJob(job_type="initial_setup", dataset_filename="diabetes.csv", rows_used=len(df), status="running")
    db.session.add(job)
    db.session.flush()

    results, best = train_all_models(
        df, app.config["MODEL_FOLDER"],
        test_size=app.config["TRAIN_TEST_SPLIT"],
        random_state=app.config["RANDOM_STATE"],
    )

    ModelMetrics.query.delete()
    for r in results:
        db.session.add(ModelMetrics(
            model_name=r["model_name"],
            accuracy=r["accuracy"], precision=r["precision"],
            recall=r["recall"], f1_score=r["f1_score"],
            confusion_matrix=json.dumps(r["confusion_matrix"]),
            confusion_matrix_plot=r.get("confusion_matrix_plot"),
            is_best=r["is_best"], training_job_id=job.id,
        ))

    job.best_model = best
    job.status = "completed"
    job.completed_at = datetime.utcnow()
    # Logistic Regression gives stable probabilities; use it unless another model is clearly better.
    production = "Logistic Regression" if "Logistic Regression" in MODEL_BUILDERS else best
    set_production_model_name(production)
    db.session.commit()

    print(f"Training complete. Best model (ROC-AUC): {best}")
    print(f"Production model for predictions: {production}")
    for r in results:
        print(f"  {r['model_name']}: Acc={r['accuracy']:.3f}, F1={r['f1_score']:.3f}")
