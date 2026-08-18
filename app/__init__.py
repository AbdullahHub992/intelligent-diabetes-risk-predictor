import os

from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    for folder in [
        app.config["UPLOAD_FOLDER"], app.config["MODEL_FOLDER"],
        app.config["PLOT_FOLDER"], os.path.join(app.config.get("BASE_DIR", "."), "instance"),
    ]:
        os.makedirs(folder, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User
    from app.security import add_security_headers

    @login_manager.user_loader
    def load_user(user_id):
        user = User.query.get(int(user_id))
        if user and not user.is_active:
            return None
        return user

    @app.after_request
    def apply_security_headers(response):
        return add_security_headers(response)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.provider import provider_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(provider_bp, url_prefix="/provider")

    @app.context_processor
    def inject_live_demo_flags():
        return {
            "live_ephemeral_db": (
                os.environ.get("RENDER") == "true" and not os.environ.get("DATABASE_URL")
            ),
        }

    @app.context_processor
    def inject_app_name():
        from config import (
            APP_NAME, PROJECT_COURSE, PROJECT_GROUP_ID,
            PROJECT_STUDENT, PROJECT_STUDENT_ID, PROJECT_SUPERVISOR, PROJECT_VERSION,
        )
        return {
            "app_name": APP_NAME,
            "project_group_id": PROJECT_GROUP_ID,
            "project_student": PROJECT_STUDENT,
            "project_student_id": PROJECT_STUDENT_ID,
            "project_supervisor": PROJECT_SUPERVISOR,
            "project_course": PROJECT_COURSE,
            "project_version": PROJECT_VERSION,
        }

    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return {"csrf_token": generate_csrf}

    @app.context_processor
    def inject_srs_context():
        from flask import request
        from app.srs_requirements import (
            ADMIN_PANEL_FR_IDS,
            FR_BY_ENDPOINT,
            SRS_FR_SUMMARY,
            USER_PANEL_FR_IDS,
        )
        return {
            "page_srs": FR_BY_ENDPOINT.get(request.endpoint),
            "srs_fr_table": SRS_FR_SUMMARY,
            "srs_user_fr_ids": USER_PANEL_FR_IDS,
            "srs_admin_fr_ids": ADMIN_PANEL_FR_IDS,
        }

    @app.context_processor
    def inject_admin_notifications():
        from flask_login import current_user
        from app.utils import get_unread_admin_feedback_count

        ctx = {"admin_unread_feedback": 0}
        if current_user.is_authenticated and current_user.is_admin:
            ctx["admin_unread_feedback"] = get_unread_admin_feedback_count()
        return ctx

    with app.app_context():
        db.create_all()
        _migrate_schema()
        _seed_defaults(app)
        from app.account_backup import restore_from_backup
        restore_from_backup(app)
        _ensure_plots_exist(app)
        from app.ml.predictor import clear_model_cache
        clear_model_cache()

    return app


def _migrate_schema():
    """Add new columns to existing SQLite DB if needed."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    migrations = [
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
        ("users", "professional_credentials", "VARCHAR(200)"),
        ("users", "security_question", "VARCHAR(200)"),
        ("users", "security_answer_hash", "VARCHAR(256)"),
        ("users", "phone", "VARCHAR(30)"),
        ("users", "address", "VARCHAR(255)"),
        ("users", "baseline_height_cm", "REAL"),
        ("users", "baseline_weight_kg", "REAL"),
        ("users", "baseline_age", "INTEGER"),
        ("users", "baseline_sex", "VARCHAR(10)"),
        ("health_records", "smoking", "VARCHAR(20)"),
        ("health_records", "physical_activity", "VARCHAR(30)"),
        ("health_records", "diet_quality", "VARCHAR(30)"),
        ("predictions", "confidence_score", "REAL"),
    ]
    existing_tables = inspector.get_table_names()
    for table, col, col_type in migrations:
        if table not in existing_tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if col not in cols:
            try:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                db.session.commit()
                inspector = inspect(db.engine)
            except Exception as exc:
                db.session.rollback()
                print(f"Migration warning ({table}.{col}): {exc}")


def _ensure_plots_exist(app):
    plot_dir = app.config["PLOT_FOLDER"]
    required = ["model_comparison.png", "correlation_heatmap.png"]
    missing = [p for p in required if not os.path.exists(os.path.join(plot_dir, p))]
    data_path = os.path.join(app.config["UPLOAD_FOLDER"], "diabetes.csv")
    if missing and os.path.exists(data_path):
        try:
            from app.ml.pipeline import clean_data, generate_eda, load_dataset
            df = clean_data(load_dataset(data_path))
            generate_eda(df, plot_dir)
        except Exception:
            pass


def _seed_defaults(app):
    from app.models import EducationResource, ProviderPatient, User
    from werkzeug.security import generate_password_hash

    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin", email="admin@diabetes.local",
            full_name="System Administrator", role="admin",
            password_hash=generate_password_hash("admin123"), is_active=True,
            security_question="city",
        )
        admin.set_security_answer("admin")
        db.session.add(admin)

    provider = User.query.filter_by(username="doctor").first()
    if not provider:
        provider = User(
            username="doctor", email="doctor@diabetes.local",
            full_name="Dr. Healthcare Provider", role="provider",
            password_hash=generate_password_hash("doctor123"), is_active=True,
            professional_credentials="MD-12345",
            security_question="city",
        )
        provider.set_security_answer("doctor")
        db.session.add(provider)
        db.session.flush()

    patient = User.query.filter_by(username="patient").first()
    if not patient:
        patient = User(
            username="patient", email="patient@diabetes.local",
            full_name="Sample Patient", role="patient",
            password_hash=generate_password_hash("patient123"), is_active=True,
            security_question="pet",
        )
        patient.set_security_answer("patient")
        db.session.add(patient)
        db.session.flush()

    if provider and patient:
        if not ProviderPatient.query.filter_by(provider_id=provider.id, patient_id=patient.id).first():
            db.session.add(ProviderPatient(provider_id=provider.id, patient_id=patient.id))

    if EducationResource.query.count() == 0:
        resources = [
            EducationResource(
                title="Understanding Diabetes Risk Factors",
                category="risk_factors",
                content="Key risk factors include high blood glucose, elevated BMI, family history, age over 45, high blood pressure, and physical inactivity.",
                external_url="https://www.diabetes.org/diabetes-risk",
            ),
            EducationResource(
                title="Prevention Strategies",
                category="prevention",
                content="Maintain a balanced diet, exercise 150+ minutes weekly, maintain healthy weight, avoid smoking, and get regular checkups.",
                external_url="https://www.cdc.gov/diabetes/prevention/",
            ),
            EducationResource(
                title="Healthy Lifestyle Guidelines",
                category="lifestyle",
                content="Eat whole grains and vegetables, manage stress, sleep 7-9 hours, and track health metrics regularly.",
            ),
            EducationResource(
                title="When to See a Doctor",
                category="general",
                content="Seek medical advice if you experience excessive thirst, frequent urination, unexplained weight loss, or blurred vision.",
            ),
            EducationResource(
                title="Monitoring Blood Glucose",
                category="lifestyle",
                content="Regular fasting glucose and HbA1c tests help detect prediabetes and diabetes early.",
            ),
        ]
        db.session.add_all(resources)

    from app.utils import get_owner_access_code, set_owner_access_code

    if not get_owner_access_code("admin"):
        set_owner_access_code(
            "admin",
            os.environ.get("OWNER_ADMIN_ACCESS_CODE", "admin2026"),
        )
    if not get_owner_access_code("doctor"):
        set_owner_access_code(
            "doctor",
            os.environ.get("OWNER_DOCTOR_ACCESS_CODE", "doctor2026"),
        )

    for username, question, answer in [
        ("admin", "city", "admin"),
        ("doctor", "city", "doctor"),
        ("patient", "pet", "patient"),
    ]:
        u = User.query.filter_by(username=username).first()
        if u and not u.security_answer_hash:
            u.security_question = question
            u.set_security_answer(answer)

    db.session.commit()
