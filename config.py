import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _load_dotenv():
    path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            value = value.strip().strip('"').strip("'")
            if key and not os.environ.get(key):
                os.environ[key] = value


_load_dotenv()


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
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "").replace(" ", "")
    MAIL_FROM = os.environ.get("MAIL_FROM") or os.environ.get("MAIL_USERNAME", "")
    # Render's free plan blocks SMTP ports, so the live site sends through Brevo instead.
    BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").replace(" ", "")
    OTP_EXPIRE_MINUTES = 10
    # Required once, on admin sign-up only.
    ADMIN_ACCESS_CODES = ("IDRP-ADMIN-01",)
