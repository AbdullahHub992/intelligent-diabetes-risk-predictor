"""Apply pending database column migrations."""
from sqlalchemy import inspect, text

from app import create_app, db

app = create_app()

MIGRATIONS = [
    ("users", "is_active", "BOOLEAN DEFAULT 1"),
    ("feedbacks", "used_in_training", "BOOLEAN DEFAULT 0"),
    ("model_metrics", "confusion_matrix_plot", "VARCHAR(255)"),
    ("model_metrics", "training_job_id", "INTEGER"),
    ("education_resources", "external_url", "VARCHAR(500)"),
    ("education_resources", "created_at", "DATETIME"),
    ("health_records", "sex", "VARCHAR(10) DEFAULT 'female'"),
    ("health_records", "systolic", "REAL DEFAULT 120"),
    ("health_records", "diastolic", "REAL DEFAULT 80"),
    ("feedbacks", "is_read", "BOOLEAN DEFAULT 1"),
]

with app.app_context():
    inspector = inspect(db.engine)
    for table, col, col_type in MIGRATIONS:
        if table not in inspector.get_table_names():
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if col in cols:
            print(f"OK: {table}.{col} exists")
            continue
        sql = f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"
        print(f"Applying: {sql}")
        db.session.execute(text(sql))
        db.session.commit()
        print(f"Added {table}.{col}")

    if "health_records" in inspector.get_table_names():
        hr_cols = {c["name"] for c in inspect(db.engine).get_columns("health_records")}
        if "blood_pressure" in hr_cols and "diastolic" in hr_cols:
            db.session.execute(text(
                "UPDATE health_records SET diastolic = blood_pressure "
                "WHERE (diastolic IS NULL OR diastolic = 0) AND blood_pressure IS NOT NULL"
            ))
            db.session.execute(text(
                "UPDATE health_records SET systolic = blood_pressure + 40 "
                "WHERE (systolic IS NULL OR systolic = 0) AND blood_pressure IS NOT NULL"
            ))
            db.session.commit()
            print("Backfilled systolic/diastolic from legacy blood_pressure")

    hr_cols = {c["name"] for c in inspect(db.engine).get_columns("health_records")}
    print("health_records columns:", sorted(hr_cols))
