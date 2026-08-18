"""SRS v1.0 functional requirements — shared by docs and website UI."""

FUNCTIONAL_REQUIREMENTS = [
    {
        "id": "FR-01",
        "uc": "UC_01",
        "title": "User Registration",
        "description": "Register as Patient or Healthcare Provider with username, email, full name, and password.",
        "panel": "user",
    },
    {
        "id": "FR-02",
        "uc": "UC_02",
        "title": "User Login with RBAC",
        "description": "Secure login for the User Panel (patients and healthcare providers) with role-based access control.",
        "panel": "user",
    },
    {
        "id": "FR-02",
        "uc": "UC_09",
        "title": "Admin Login with RBAC",
        "description": "Administrator login with username, password, and role enforcement.",
        "panel": "admin",
    },
    {
        "id": "FR-03",
        "uc": None,
        "title": "Password Recovery",
        "description": "Recover password using the registered username or email, then set a new hashed password.",
        "panel": "user",
    },
    {
        "id": "FR-04",
        "uc": "UC_06",
        "title": "Password Change",
        "description": "Change password; current password required for verification. The password is hashed.",
        "panel": "both",
    },
    {
        "id": "FR-05",
        "uc": None,
        "title": "Profile Management",
        "description": "View and update contact information and baseline physical metrics.",
        "panel": "both",
    },
    {
        "id": "FR-06",
        "uc": "UC_03",
        "title": "Health Data Input & Prediction",
        "description": "Enter the eight clinical features plus lifestyle habits; generate a risk prediction with confidence.",
        "panel": "user",
    },
    {
        "id": "FR-07",
        "uc": "UC_04",
        "title": "Prediction History & Longitudinal Tracking",
        "description": "View prediction history and track glucose, BMI, and risk trends over time.",
        "panel": "user",
    },
    {
        "id": "FR-08",
        "uc": None,
        "title": "Risk Factor Analysis & Explanation",
        "description": "Explain Result — interpretable ML and clinical threshold explanations.",
        "panel": "user",
    },
    {
        "id": "FR-09",
        "uc": None,
        "title": "Personalized Recommendations",
        "description": "Lifestyle and medical follow-up advice based on risk level and health values.",
        "panel": "user",
    },
    {
        "id": "FR-10",
        "uc": None,
        "title": "Dashboard & Trend Visualization",
        "description": "Interactive user dashboard with Chart.js prediction trends and insights.",
        "panel": "user",
    },
    {
        "id": "FR-11",
        "uc": "UC_05",
        "title": "Report Export (PDF/CSV)",
        "description": "Export health reports with format and prediction scope selection.",
        "panel": "user",
    },
    {
        "id": "FR-12",
        "uc": None,
        "title": "Education",
        "description": "Browse diabetes prevention and lifestyle education content.",
        "panel": "user",
    },
    {
        "id": "FR-13",
        "uc": None,
        "title": "Clinical Decision Support",
        "description": "Healthcare providers review assigned patients, predictions, and add clinical notes.",
        "panel": "user",
    },
    {
        "id": "FR-14",
        "uc": None,
        "title": "Feedback",
        "description": "Submit prediction ratings and actual clinical outcomes for model improvement.",
        "panel": "user",
    },
    {
        "id": "FR-15",
        "uc": "UC_07",
        "title": "Logout",
        "description": "Secure session termination for User and Admin (same UC_07 numbering).",
        "panel": "both",
    },
    {
        "id": "FR-16",
        "uc": "UC_10",
        "title": "Dataset Ingestion",
        "description": "Import clinical diabetes CSV datasets for training and EDA.",
        "panel": "admin",
    },
    {
        "id": "FR-17",
        "uc": "UC_11",
        "title": "EDA & Preprocessing",
        "description": "Exploratory analysis, cleaning, scaling, and 70/30 train-test split.",
        "panel": "admin",
    },
    {
        "id": "FR-18",
        "uc": "UC_12",
        "title": "Model Training & Comparison",
        "description": "Train and compare Neural Network, SVM, Decision Tree, and Logistic Regression.",
        "panel": "admin",
    },
    {
        "id": "FR-19",
        "uc": None,
        "title": "Model Persistence & Retraining",
        "description": "Persist models with joblib; retrain from verified feedback; set production model.",
        "panel": "admin",
    },
    {
        "id": "FR-20",
        "uc": None,
        "title": "Account Management (Admin)",
        "description": "Create, edit, activate/deactivate users and reset passwords.",
        "panel": "admin",
    },
]

SRS_FR_TABLE = FUNCTIONAL_REQUIREMENTS

# One row per FR id for the home-page compliance table (FR-01 … FR-20).
_UNIQUE = {}
for row in FUNCTIONAL_REQUIREMENTS:
    if row["id"] not in _UNIQUE:
        _UNIQUE[row["id"]] = row
SRS_FR_SUMMARY = [_UNIQUE[f"FR-{i:02d}"] for i in range(1, 21)]

USER_PANEL_FR_IDS = sorted({r["id"] for r in FUNCTIONAL_REQUIREMENTS if r["panel"] in ("user", "both")})
ADMIN_PANEL_FR_IDS = sorted({r["id"] for r in FUNCTIONAL_REQUIREMENTS if r["panel"] in ("admin", "both")})

# Map Flask endpoints to page-level SRS banner (first match wins for shared pages).
FR_BY_ENDPOINT = {
    "auth.register": {**FUNCTIONAL_REQUIREMENTS[0], "title": "User Registration"},
    "auth.user_login": {**FUNCTIONAL_REQUIREMENTS[1], "title": "User Login"},
    "auth.login_admin": {**FUNCTIONAL_REQUIREMENTS[2], "title": "Admin Login"},
    "auth.forgot_password": {**FUNCTIONAL_REQUIREMENTS[3]},
    "auth.change_password": {**FUNCTIONAL_REQUIREMENTS[4]},
    "auth.profile_settings": {**FUNCTIONAL_REQUIREMENTS[5]},
    "auth.register_admin": {
        "id": "FR-20",
        "uc": "UC_08",
        "title": "Admin Registration",
        "description": "Register system administrator with username, email, full name, and password.",
        "panel": "admin",
    },
    "main.health_data": {**FUNCTIONAL_REQUIREMENTS[6]},
    "main.edit_health_record": {**FUNCTIONAL_REQUIREMENTS[6], "title": "Update Health Data & Recalculate Risk"},
    "main.my_health_records": {
        "id": "FR-07",
        "uc": None,
        "title": "Prediction History",
        "description": "View past health records and linked prediction results.",
        "panel": "user",
    },
    "main.progress": {**FUNCTIONAL_REQUIREMENTS[7]},
    "main.prediction_detail": {**FUNCTIONAL_REQUIREMENTS[8]},
    "main.dashboard": {**FUNCTIONAL_REQUIREMENTS[10]},
    "main.export_report": {**FUNCTIONAL_REQUIREMENTS[11]},
    "main.education": {**FUNCTIONAL_REQUIREMENTS[12]},
    "main.feedback": {**FUNCTIONAL_REQUIREMENTS[14]},
    "provider.provider_dashboard": {**FUNCTIONAL_REQUIREMENTS[13]},
    "provider.clinical_support": {**FUNCTIONAL_REQUIREMENTS[13], "title": "Clinical Decision Support Detail"},
    "provider.patient_detail": {**FUNCTIONAL_REQUIREMENTS[13], "title": "Assigned Patient Review"},
    "admin.upload_dataset": {**FUNCTIONAL_REQUIREMENTS[16]},
    "admin.eda": {**FUNCTIONAL_REQUIREMENTS[17]},
    "admin.train_models": {**FUNCTIONAL_REQUIREMENTS[18]},
    "admin.model_settings": {**FUNCTIONAL_REQUIREMENTS[19]},
    "admin.training_history": {**FUNCTIONAL_REQUIREMENTS[19], "title": "Training History"},
    "admin.retrain_feedback": {**FUNCTIONAL_REQUIREMENTS[19], "title": "Retrain from Feedback"},
    "admin.manage_users": {**FUNCTIONAL_REQUIREMENTS[20]},
    "admin.create_user": {**FUNCTIONAL_REQUIREMENTS[20], "title": "Create User Account"},
    "admin.edit_user": {**FUNCTIONAL_REQUIREMENTS[20], "title": "Edit User Account"},
    "admin.manage_education": {**FUNCTIONAL_REQUIREMENTS[12], "title": "Education Content (Admin)", "panel": "admin"},
    "admin.edit_education": {**FUNCTIONAL_REQUIREMENTS[12], "title": "Education Content (Admin)", "panel": "admin"},
    "admin.view_feedback": {**FUNCTIONAL_REQUIREMENTS[14], "title": "Feedback Review (Retraining)", "panel": "admin"},
    "admin.view_feedback_detail": {**FUNCTIONAL_REQUIREMENTS[14], "title": "Feedback Detail", "panel": "admin"},
    "admin.manage_assignments": {**FUNCTIONAL_REQUIREMENTS[13], "title": "Patient–Provider Assignment", "panel": "admin"},
    "admin.admin_dashboard": {
        "id": "FR-16",
        "uc": None,
        "title": "Admin Panel Dashboard",
        "description": "Dataset workflow, model training, account management, and system monitoring.",
        "panel": "admin",
    },
}
