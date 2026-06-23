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
    def inject_app_name():
        from config import APP_NAME
        return {"app_name": APP_NAME}

    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return {"csrf_token": generate_csrf}

    @app.context_processor
    def inject_admin_notifications():
        from flask_login import current_user
        from app.utils import get_unread_admin_feedback_count, get_unread_admin_reports_count, get_unread_doctor_forwards_count

        ctx = {"admin_unread_reports": 0, "admin_unread_feedback": 0, "doctor_unread_forwards": 0, "patient_unread_remarks": 0}
        if current_user.is_authenticated:
            if current_user.is_admin:
                ctx["admin_unread_reports"] = get_unread_admin_reports_count()
                ctx["admin_unread_feedback"] = get_unread_admin_feedback_count()
            if current_user.is_provider:
                ctx["doctor_unread_forwards"] = get_unread_doctor_forwards_count(current_user.id)
            if current_user.is_patient:
                from app.utils import get_unread_doctor_remarks_count
                ctx["patient_unread_remarks"] = get_unread_doctor_remarks_count(current_user.id)
        return ctx

    with app.app_context():
        db.create_all()
        _migrate_schema()
        _seed_defaults(app)
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
        db.session.add(User(
            username="admin", email="admin@diabetes.local",
            full_name="System Administrator", role="admin",
            password_hash=generate_password_hash("admin123"), is_active=True,
        ))

    provider = User.query.filter_by(username="doctor").first()
    if not provider:
        provider = User(
            username="doctor", email="doctor@diabetes.local",
            full_name="Dr. Healthcare Provider", role="provider",
            password_hash=generate_password_hash("doctor123"), is_active=True,
        )
        db.session.add(provider)
        db.session.flush()

    patient = User.query.filter_by(username="patient").first()
    if not patient:
        patient = User(
            username="patient", email="patient@diabetes.local",
            full_name="Sample Patient", role="patient",
            password_hash=generate_password_hash("patient123"), is_active=True,
        )
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

    db.session.commit()
