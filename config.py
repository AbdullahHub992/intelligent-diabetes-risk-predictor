import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_uri():
    url = os.environ.get("DATABASE_URL")
    if url:
        # Render/Neon may provide postgres:// — SQLAlchemy needs postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'diabetes.db')}"


APP_NAME = "Intelligent Diabetes Risk Predictor"

# SRS project metadata (Spring 2026 CS619)
PROJECT_GROUP_ID = "S26PROJECT0C0EB"
PROJECT_STUDENT = "Muhammad Shahmeer Akhtar"
PROJECT_STUDENT_ID = "BC220415649"
PROJECT_SUPERVISOR = "Komal Khawer"
PROJECT_COURSE = "CS619 — Final Project"
PROJECT_VERSION = "1.0"


class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get("SECRET_KEY", "diabetes-risk-predictor-cs619-secret-key")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "data")
    MODEL_FOLDER = os.path.join(BASE_DIR, "saved_models")
    PLOT_FOLDER = os.path.join(BASE_DIR, "app", "static", "plots")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    TRAIN_TEST_SPLIT = 0.3
    RANDOM_STATE = 42
    REMEMBER_COOKIE_DURATION = 86400
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("RENDER") == "true"
    WTF_CSRF_ENABLED = True
