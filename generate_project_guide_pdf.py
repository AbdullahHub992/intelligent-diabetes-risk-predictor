"""Generate a detailed Project Understanding Guide PDF."""

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).resolve().parent / "docs" / "Project_Understanding_Guide.pdf"
LIVE_URL = "https://intelligent-diabetes-risk-predictor.onrender.com"


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontSize=22, spaceAfter=12,
            textColor=colors.HexColor("#1565C0"),
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"], fontSize=12, spaceAfter=8, textColor=colors.grey,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontSize=16, spaceBefore=18, spaceAfter=10,
            textColor=colors.HexColor("#0D47A1"),
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontSize=13, spaceBefore=12, spaceAfter=6,
            textColor=colors.HexColor("#1565C0"),
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontSize=10.5, leading=15, spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"], fontSize=10.5, leading=15, spaceAfter=4,
            leftIndent=14, bulletIndent=0,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"], fontSize=9, leading=12, textColor=colors.grey,
        ),
    }


def _b(story, styles, text):
    story.append(Paragraph(f"• {text}", styles["bullet"]))


def _p(story, styles, text):
    story.append(Paragraph(text, styles["body"]))


def _h1(story, styles, text):
    story.append(Paragraph(text, styles["h1"]))


def _h2(story, styles, text):
    story.append(Paragraph(text, styles["h2"]))


def build_pdf():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50,
    )
    story = []

    # ── Cover ──────────────────────────────────────────────────────────
    story.append(Paragraph("Intelligent Diabetes Risk Predictor", styles["title"]))
    story.append(Paragraph("Detailed Project Understanding Guide", styles["subtitle"]))
    story.append(Paragraph("CS619 Final Project", styles["subtitle"]))
    story.append(Paragraph(f"Prepared: {date.today().strftime('%B %d, %Y')}", styles["small"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1565C0")))
    story.append(Spacer(1, 0.1 * inch))

    _p(story, styles,
       "This document explains the complete Intelligent Diabetes Risk Predictor system — "
       "what it does, how it is built, how each role uses it, and how the machine learning "
       "pipeline works from data input to risk prediction.")
    _p(story, styles,
       "<b>Important:</b> This is a <b>decision-support</b> tool for education and risk awareness. "
       "It is <b>not</b> a medical diagnosis. Always consult a qualified healthcare professional "
       "for clinical decisions.")

  # ── 1. Introduction ────────────────────────────────────────────────
    _h1(story, styles, "1. Introduction")
    _h2(story, styles, "1.1 What Is This Project?")
    _p(story, styles,
       "The Intelligent Diabetes Risk Predictor is a full-stack web application that uses "
       "machine learning to estimate a person's risk of developing diabetes based on clinical "
       "and lifestyle measurements. It was developed as the CS619 Final Project under "
       "supervision of Komal Khawer (komal.khawer@vu.edu.pk).")
    _p(story, styles,
       "Unlike a simple Python script that only prints a prediction, this is a complete system "
       "with user accounts, role-based access, a database, security controls, dashboards, "
       "report export, education content, clinical workflows, and cloud deployment.")

    _h2(story, styles, "1.2 Why This Project Matters")
    for item in [
        "Diabetes affects millions worldwide; early detection enables prevention.",
        "Multiple health factors (glucose, BMI, blood pressure, age, etc.) interact in complex ways — ML can analyze them together.",
        "A web interface makes risk assessment accessible to patients at home.",
        "Doctors can use it as clinical decision support for assigned patients.",
        "Admins can manage models, data, and system quality over time.",
    ]:
        _b(story, styles, item)

    _h2(story, styles, "1.3 What the System Is NOT")
    _b(story, styles, "It does not replace a doctor or laboratory diagnosis.")
    _b(story, styles, "It does not use real-time hospital equipment or EHR integration.")
    _b(story, styles, "It is trained on a historical research dataset (Pima Indians), not your local population.")
    _b(story, styles, "Predictions are probability estimates, not certainties.")

  # ── 2. System Overview ─────────────────────────────────────────────
    _h1(story, styles, "2. System Overview")
    _h2(story, styles, "2.1 Three User Roles")
    _p(story, styles, "<b>Patient</b> — End users who enter their health data, receive risk predictions, "
       "track progress over time, read education content, submit feedback, and export reports.")
    _p(story, styles, "<b>Healthcare Provider (Doctor)</b> — Clinicians who view assigned patients only, "
       "review predictions and trends, add clinical notes, use decision-support tools, and "
       "respond to cases forwarded by the administrator.")
    _p(story, styles, "<b>Administrator</b> — System managers who control users, datasets, model training, "
       "education content, feedback review, audit logs, and the clinical escalation workflow.")

    _h2(story, styles, "2.2 Core Capabilities (19 CS619 Requirements)")
    for item in [
        "User management with role-based access control (Patient, Provider, Admin)",
        "Health data input and admin dataset import",
        "Exploratory data analysis (EDA) with charts",
        "Data preprocessing, scaling, and 70/30 train-test split",
        "Four ML models: Neural Network, SVM, Decision Tree, Logistic Regression",
        "Evaluation metrics: Accuracy, Precision, Recall, F1, Confusion Matrix",
        "Model comparison, auto-selection, and admin override",
        "Model persistence with joblib",
        "ML-based risk factor analysis and clinical threshold alerts",
        "Personalized recommendations by risk level",
        "Longitudinal tracking with trend alerts",
        "Role-specific dashboards with Chart.js",
        "PDF and CSV report export",
        "Education resources with admin content management",
        "Clinical decision support and provider notes",
        "Feedback collection and model retraining from verified outcomes",
        "Admin panel: users, assignments, training history, audit logs",
        "Performance optimization: model caching, fast inference",
        "Security: password hashing, CSRF, rate limiting, audit trail, consent",
    ]:
        _b(story, styles, item)

  # ── 3. Architecture ──────────────────────────────────────────────────
    _h1(story, styles, "3. System Architecture")
    _h2(story, styles, "3.1 Three-Tier Design")
    _p(story, styles, "The application follows a classic three-tier monolithic architecture:")
    _b(story, styles, "<b>Presentation Tier:</b> Jinja2 HTML templates, Bootstrap CSS, Chart.js charts, static plot images.")
    _b(story, styles, "<b>Application Tier:</b> Flask web framework with blueprints (auth, main, admin, provider), WTForms validation, Flask-Login sessions.")
    _b(story, styles, "<b>Data &amp; ML Tier:</b> SQLAlchemy ORM + SQLite/PostgreSQL database, CSV dataset in data/, trained models in saved_models/.")

    _h2(story, styles, "3.2 Flask Blueprints")
    _b(story, styles, "<b>auth_bp</b> — Login (patient/doctor/admin portals), registration, profile, logout.")
    _b(story, styles, "<b>main_bp</b> — Patient dashboard, health data entry, predictions, progress, education, feedback, reports.")
    _b(story, styles, "<b>admin_bp</b> (prefix /admin) — Dataset upload, EDA, model training, user management, assignments, CMS, audit.")
    _b(story, styles, "<b>provider_bp</b> (prefix /provider) — Doctor dashboard, patient detail, clinical support, forwarded reports.")

    _h2(story, styles, "3.3 Application Factory (create_app)")
    _p(story, styles, "The app is created via create_app() in app/__init__.py. On startup it:")
    for step in [
        "Loads configuration from config.py (database URI, folders, security settings).",
        "Creates required folders: data/, saved_models/, app/static/plots/, instance/.",
        "Initializes SQLAlchemy and Flask-Login.",
        "Registers all blueprints and security headers.",
        "Runs database schema migrations for new columns.",
        "Seeds default users, education resources, and owner access codes.",
        "Regenerates missing EDA plots if the dataset exists.",
        "Clears the ML model cache so fresh models are loaded.",
    ]:
        _b(story, styles, step)

    _h2(story, styles, "3.4 Project Folder Structure")
    for line in [
        "app/routes/       — auth.py, main.py, admin.py, provider.py",
        "app/ml/           — pipeline.py, predictor.py, explainability.py, recommendations.py, retrain.py, reports.py",
        "app/templates/    — HTML pages for all roles",
        "app/static/       — CSS and generated plot images",
        "app/models.py     — Database table definitions",
        "app/forms.py      — WTForms with validation rules",
        "app/security.py   — Rate limiting and HTTP security headers",
        "data/             — diabetes.csv dataset",
        "saved_models/     — Trained .joblib model files",
        "instance/         — SQLite database (local dev)",
        "docs/             — SRS, User Manual, Test Plan, PDFs",
        "tests/            — pytest unit tests",
        "config.py         — App configuration",
        "run.py            — Development server entry point",
        "train_initial.py  — First-time model training script",
        "setup_data.py     — Dataset download script",
        "Dockerfile        — Production container",
        "render.yaml       — Render cloud deployment blueprint",
    ]:
        _b(story, styles, line)

    story.append(PageBreak())

  # ── 4. Technology Stack ───────────────────────────────────────────
    _h1(story, styles, "4. Technology Stack")
    _b(story, styles, "<b>Python 3.12</b> — Primary programming language.")
    _b(story, styles, "<b>Flask 3.x</b> — Lightweight web framework for routing, templates, and sessions.")
    _b(story, styles, "<b>Flask-SQLAlchemy</b> — Object-relational mapping for database tables.")
    _b(story, styles, "<b>Flask-Login</b> — Session-based authentication and current_user management.")
    _b(story, styles, "<b>Flask-WTF / WTForms</b> — Form handling with CSRF protection and validation.")
    _b(story, styles, "<b>scikit-learn</b> — ML algorithms, preprocessing, metrics, and pipelines.")
    _b(story, styles, "<b>pandas / numpy</b> — Data manipulation for training and inference.")
    _b(story, styles, "<b>matplotlib / seaborn</b> — EDA plots, confusion matrices, model comparison charts.")
    _b(story, styles, "<b>joblib</b> — Serialize and load trained ML pipelines.")
    _b(story, styles, "<b>ReportLab</b> — Generate PDF reports for patients and admins.")
    _b(story, styles, "<b>Chart.js</b> — Interactive charts on dashboards and progress page.")
    _b(story, styles, "<b>Bootstrap</b> — Responsive UI layout and styling.")
    _b(story, styles, "<b>Gunicorn</b> — Production WSGI server inside Docker.")
    _b(story, styles, "<b>SQLite / PostgreSQL</b> — Local dev vs. production persistent database.")
    _b(story, styles, "<b>Render + Docker</b> — Cloud hosting with health checks.")

  # ── 5. Database Design ────────────────────────────────────────────
    _h1(story, styles, "5. Database Design")
    _h2(story, styles, "5.1 Main Tables")
    _p(story, styles, "<b>users</b> — Stores accounts: username, email, hashed password, full name, role (patient/provider/admin), active status.")
    _p(story, styles, "<b>health_records</b> — Patient vitals per entry: sex, pregnancies, glucose, systolic/diastolic BP, skin thickness, insulin, BMI, diabetes pedigree, age, timestamp.")
    _p(story, styles, "<b>predictions</b> — ML output linked to a health record: model name, probability, risk level (Low/Moderate/High), explanation JSON, recommendations JSON.")
    _p(story, styles, "<b>model_metrics</b> — Training results per model: accuracy, precision, recall, F1, confusion matrix, is_best flag.")
    _p(story, styles, "<b>training_jobs</b> — Metadata for each training run: type, rows used, feedback rows, best model, status.")
    _p(story, styles, "<b>feedbacks</b> — User ratings and actual clinical outcomes for retraining.")
    _p(story, styles, "<b>provider_patients</b> — Many-to-many link between doctors and their assigned patients.")
    _p(story, styles, "<b>clinical_notes</b> — Doctor notes attached to a patient prediction.")
    _p(story, styles, "<b>education_resources</b> — CMS articles: title, category, content, optional external URL.")
    _p(story, styles, "<b>audit_logs</b> — Security trail: user, action, resource, IP address, timestamp.")
    _p(story, styles, "<b>admin_report_submissions</b> — Patient reports sent to admin for review.")
    _p(story, styles, "<b>doctor_report_forwards</b> — Admin forwards patient reports to assigned doctors.")
    _p(story, styles, "<b>doctor_report_remarks</b> — Doctor remarks sent back to patients.")

    _h2(story, styles, "5.2 Key Relationships")
    _b(story, styles, "One User has many HealthRecords and Predictions.")
    _b(story, styles, "Each HealthRecord generates one Prediction.")
    _b(story, styles, "Each Prediction can have Feedback entries.")
    _b(story, styles, "ProviderPatient links doctors to patients they are allowed to view.")
    _b(story, styles, "TrainingJob records produce multiple ModelMetrics rows.")

    _h2(story, styles, "5.3 Database Configuration")
    _p(story, styles, "Locally, SQLite stores data at instance/diabetes.db. In production, set the "
       "DATABASE_URL environment variable to a PostgreSQL connection string (e.g. from Neon). "
       "Without PostgreSQL on Render, data may reset when the app redeploys.")

  # ── 6. Machine Learning ───────────────────────────────────────────
    _h1(story, styles, "6. Machine Learning Pipeline")
    _h2(story, styles, "6.1 Dataset")
    _p(story, styles, "The system uses the Pima Indians Diabetes Dataset (UCI / Kaggle diabeticprediction). "
       "It contains 8 input features and a binary outcome (0 = no diabetes, 1 = diabetes):")
    for feat in [
        "Pregnancies — Number of times pregnant",
        "Glucose — Plasma glucose concentration (mg/dL)",
        "BloodPressure — Diastolic blood pressure (mm Hg)",
        "SkinThickness — Triceps skin fold thickness (mm)",
        "Insulin — 2-hour serum insulin (mu U/ml)",
        "BMI — Body mass index (kg/m²)",
        "DiabetesPedigreeFunction — Family history score",
        "Age — Age in years",
    ]:
        _b(story, styles, feat)

    _h2(story, styles, "6.2 Data Preprocessing")
    for step in [
        "Zeros in Glucose, BloodPressure, SkinThickness, Insulin, and BMI are treated as missing values (common in this dataset).",
        "Missing values are imputed using the median (SimpleImputer).",
        "All features are standardized with StandardScaler (zero mean, unit variance).",
        "Data is split 70% training / 30% testing with stratification to preserve class balance.",
        "Random state is fixed at 42 for reproducible results.",
    ]:
        _b(story, styles, step)

    _h2(story, styles, "6.3 Four ML Models")
    _b(story, styles, "<b>Neural Network (MLPClassifier):</b> Hidden layers (32, 16), ReLU activation, early stopping.")
    _b(story, styles, "<b>SVM (SVC):</b> RBF kernel, probability enabled, balanced class weights.")
    _b(story, styles, "<b>Decision Tree:</b> Max depth 5, balanced class weights.")
    _b(story, styles, "<b>Logistic Regression:</b> Max 2000 iterations, balanced class weights.")

    _p(story, styles, "Each model is wrapped in a scikit-learn Pipeline: Imputer → Scaler → Classifier. "
       "This ensures the same preprocessing is applied during both training and live prediction.")

    _h2(story, styles, "6.4 Model Evaluation &amp; Selection")
    _p(story, styles, "After training, each model is evaluated on the 30% test set:")
    _b(story, styles, "<b>Accuracy</b> — Overall correct predictions.")
    _b(story, styles, "<b>Precision</b> — Of predicted diabetics, how many are actually diabetic.")
    _b(story, styles, "<b>Recall</b> — Of actual diabetics, how many the model detected.")
    _b(story, styles, "<b>F1-Score</b> — Harmonic mean of precision and recall (used for comparison).")
    _b(story, styles, "<b>ROC-AUC</b> — Area under the receiver operating characteristic curve.")
    _b(story, styles, "<b>Confusion Matrix</b> — Visual heatmap saved as PNG per model.")
    _p(story, styles, "The model with the highest ROC-AUC is marked as best. A separate production pipeline "
       "(default: Logistic Regression) is trained on all data for patient-facing predictions. "
       "Admin can override the production model via Model Settings.")

    _h2(story, styles, "6.5 Live Prediction Flow")
    for step in [
        "Patient submits the health data form.",
        "Form values are saved as a HealthRecord in the database.",
        "record_to_frame() converts the record to a pandas DataFrame matching training features.",
        "Systolic and diastolic BP are combined into mean arterial pressure: (2×systolic + diastolic) / 3.",
        "Family history yes/no is mapped to pedigree values: 0.28 (no) or 0.65 (yes).",
        "The saved production pipeline loads from saved_models/ (cached in memory).",
        "predict_proba() returns the diabetes probability.",
        "Risk level is assigned: Low (&lt;35%), Moderate (35–65%), High (&gt;65%).",
        "explain_prediction() generates feature importance + clinical threshold alerts.",
        "generate_recommendation_plan() creates personalized lifestyle and medical advice.",
        "Results are saved in the predictions table and displayed to the patient.",
    ]:
        _b(story, styles, step)

    _h2(story, styles, "6.6 Explainability")
    _p(story, styles, "The system uses a hybrid explanation approach:")
    _b(story, styles, "<b>ML Feature Importance:</b> Top contributing features from model coefficients (logistic regression) or feature importances (decision tree).")
    _b(story, styles, "<b>Clinical Thresholds:</b> Checks if values exceed medical guidelines — e.g. glucose &gt; 140, BMI &gt; 30, age &gt; 45, systolic &gt; 140.")
    _p(story, styles, "Both are combined into a JSON explanation shown on the prediction result page.")

    _h2(story, styles, "6.7 Recommendations")
    _p(story, styles, "Recommendations are structured by risk level:")
    _b(story, styles, "<b>Low risk:</b> Maintain healthy habits, annual checkup, balanced diet, 150 min/week exercise.")
    _b(story, styles, "<b>Moderate risk:</b> Doctor appointment within 2–4 weeks, fasting glucose and HbA1c tests, diet changes, daily walking.")
    _b(story, styles, "<b>High risk:</b> Urgent medical consultation, strict diet control, blood sugar monitoring, weight management.")
    _p(story, styles, "Additional targeted advice is added based on which specific features are elevated (high glucose, high BMI, etc.).")

    _h2(story, styles, "6.8 Model Retraining")
    _p(story, styles, "Patients and providers can submit feedback with the actual clinical outcome (diabetic or not). "
       "Admin reviews feedback and triggers retraining. Verified feedback rows are merged with the original "
       "dataset, models are retrained, and new metrics are stored in training_jobs and model_metrics.")

    story.append(PageBreak())

  # ── 7. Role Features ──────────────────────────────────────────────
    _h1(story, styles, "7. Features by Role")
    _h2(story, styles, "7.1 Patient Features")
    for item in [
        "Register with consent checkbox / Login at /login/patient",
        "Dashboard with latest prediction, trend chart, and risk alert",
        "Health Data form — enter vitals with inline help (averages, units, clinical ranges)",
        "Instant ML prediction with risk level, explanation, and recommendations",
        "My Health Records — view and edit past entries (re-triggers prediction)",
        "Progress page — Chart.js line chart of risk probability over time",
        "Education — browse prevention and lifestyle articles",
        "Feedback — rate prediction accuracy, submit actual clinical outcome",
        "Send Report to Admin — escalate high-risk cases with a message",
        "Notifications — read doctor remarks on your reports",
        "Export PDF and CSV health reports",
    ]:
        _b(story, styles, item)

    _h2(story, styles, "7.2 Doctor (Provider) Features")
    for item in [
        "Login at /login/doctor with owner access code",
        "Clinical dashboard — assigned patients, high-risk cases highlighted",
        "Patient detail — health records, predictions, trend charts",
        "Clinical Support — ML risk analysis view + add clinical notes",
        "Forwarded Reports — cases sent by admin with admin notes",
        "Add remarks to patients (patient receives notification)",
        "Export patient reports as PDF or CSV",
        "Submit feedback on prediction accuracy",
    ]:
        _b(story, styles, item)

    _h2(story, styles, "7.3 Admin Features")
    for item in [
        "Login at /login/admin with owner access code",
        "Admin dashboard — system statistics and quick links",
        "Upload Dataset — import CSV with required columns",
        "EDA — summary statistics, correlation heatmap, histograms, outcome distribution",
        "Train Models — train all 4 algorithms, view comparison chart",
        "Model Settings — set which model is used for live patient predictions",
        "Retrain from Feedback — incorporate verified patient outcomes",
        "User Management — create, edit roles, activate/deactivate, reset passwords",
        "Assignments — link doctors to patients",
        "Education CMS — add, edit, delete prevention articles",
        "Feedback Review — read patient feedback, mark as read",
        "Received Reports — triage patient reports, forward to doctors",
        "Training History — view past training jobs and metrics",
        "Audit Logs — monitor security-sensitive actions",
    ]:
        _b(story, styles, item)

  # ── 8. Security ───────────────────────────────────────────────────
    _h1(story, styles, "8. Security Design")
    _b(story, styles, "<b>Password Hashing:</b> Werkzeug generate_password_hash — passwords never stored in plain text.")
    _b(story, styles, "<b>CSRF Protection:</b> Flask-WTF tokens on every form submission.")
    _b(story, styles, "<b>Role-Based Access Control:</b> @role_required decorator blocks unauthorized route access.")
    _b(story, styles, "<b>Owner Access Codes:</b> Admin and doctor logins require an extra private code beyond password.")
    _b(story, styles, "<b>Login Rate Limiting:</b> Max 5 failed attempts per IP+username in 5 minutes.")
    _b(story, styles, "<b>Session Security:</b> HttpOnly cookies, SameSite=Lax, Secure flag on production.")
    _b(story, styles, "<b>HTTP Security Headers:</b> X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy.")
    _b(story, styles, "<b>Audit Logging:</b> Login, predictions, training, user changes recorded with IP.")
    _b(story, styles, "<b>Consent:</b> Required checkbox on patient registration.")
    _b(story, styles, "<b>Data Isolation:</b> Doctors only see assigned patients; patients only see own data.")

  # ── 9. Workflows ──────────────────────────────────────────────────
    _h1(story, styles, "9. Key Workflows")
    _h2(story, styles, "9.1 Patient Prediction Workflow")
    for step in [
        "Patient logs in → opens Health Data page",
        "Enters vitals (glucose, BP, BMI, age, etc.) with form validation",
        "System saves HealthRecord → runs ML pipeline → saves Prediction",
        "Patient sees risk level, probability, top risk factors, and recommendations",
        "Patient can view progress over time, export report, or send to admin",
    ]:
        _b(story, styles, step)

    _h2(story, styles, "9.2 Admin Model Training Workflow")
    for step in [
        "Admin uploads or uses existing diabetes.csv dataset",
        "Views EDA charts (correlation, distributions, outcome balance)",
        "Clicks Train Models — all 4 algorithms train and evaluate",
        "Reviews comparison chart and metrics table",
        "Optionally overrides production model in Model Settings",
        "Patients now receive predictions from the selected model",
    ]:
        _b(story, styles, step)

    _h2(story, styles, "9.3 Clinical Escalation Workflow")
    for step in [
        "Patient sends report to Admin (with optional message)",
        "Admin reviews report in Received Reports",
        "Admin forwards report to an assigned doctor with a note",
        "Doctor reviews in Forwarded Reports, adds clinical remark",
        "Patient sees remark in Notifications",
        "Patient can submit feedback with actual outcome → Admin retrains model",
    ]:
        _b(story, styles, step)

  # ── 10. Setup & Deployment ──────────────────────────────────────────
    _h1(story, styles, "10. Installation &amp; Deployment")
    _h2(story, styles, "10.1 Local Setup")
    for step in [
        "cd Intelligent_Diabetes_Risk_Predictor",
        "pip install -r requirements.txt",
        "python setup_data.py          (downloads dataset)",
        "python train_initial.py       (trains models, generates plots)",
        "python run.py                 (starts server at http://localhost:5000)",
    ]:
        _b(story, styles, step)

    _h2(story, styles, "10.2 Demo Accounts")
    _b(story, styles, "Patient: username patient / password patient123 (no owner code)")
    _b(story, styles, "Doctor: username doctor / password doctor123 / owner code doctor2026")
    _b(story, styles, "Admin: username admin / password admin123 / owner code admin2026")

    _h2(story, styles, "10.3 Production Deployment (Render)")
    for step in [
        "Push project to GitHub.",
        "On Render: New + → Blueprint → select repository.",
        "Set OWNER_ADMIN_ACCESS_CODE and OWNER_DOCTOR_ACCESS_CODE environment variables.",
        "Optional: add DATABASE_URL for PostgreSQL persistence (Neon free tier).",
        "First build takes 5–8 minutes. App URL: " + LIVE_URL,
        "Health check endpoint: /health",
        "Free tier sleeps after ~15 min idle; first load after sleep takes 30–60 seconds.",
    ]:
        _b(story, styles, step)

    _h2(story, styles, "10.4 Docker")
    _p(story, styles, "The Dockerfile uses python:3.12-slim, installs dependencies, copies app code with "
       "dataset and pre-trained models for offline-safe cold start. Gunicorn serves the app on port 10000 "
       "with 1 worker and 2 threads.")

  # ── 11. Testing ─────────────────────────────────────────────────────
    _h1(story, styles, "11. Testing")
    _p(story, styles, "Unit tests are in the tests/ folder and run with: python -m pytest tests/ -v")
    _p(story, styles, "A manual test plan covering all roles and features is in docs/TEST_PLAN.md.")
    _p(story, styles, "Additional utility scripts exist for smoke checks, score verification, and form debugging.")

  # ── 12. Limitations & Future ────────────────────────────────────────
    _h1(story, styles, "12. Limitations &amp; Future Enhancements")
    _h2(story, styles, "12.1 Current Limitations")
    for item in [
        "Trained on Pima Indians dataset — may not generalize to all populations.",
        "Only 8 features — not a comprehensive clinical assessment.",
        "Not a diagnostic tool — educational decision support only.",
        "Free hosting has cold-start delays and limited resources.",
        "No mobile app, SMS/email alerts, or EHR/hospital system integration.",
        "SQLite data on Render resets on redeploy without PostgreSQL.",
    ]:
        _b(story, styles, item)

    _h2(story, styles, "12.2 Possible Future Improvements")
    for item in [
        "Larger and more diverse training datasets.",
        "SHAP/LIME for deeper model explainability.",
        "REST API for mobile clients.",
        "Multi-factor authentication for admin and doctor accounts.",
        "Email/SMS notifications for high-risk alerts.",
        "HL7/FHIR integration with hospital EHR systems.",
        "Real-time model monitoring and drift detection.",
        "Alembic database migrations for production schema management.",
    ]:
        _b(story, styles, item)

    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.1 * inch))
    _p(story, styles,
       "<b>Disclaimer:</b> This application provides an educational risk estimate based on statistical "
       "models trained on a public dataset. It does not replace professional medical advice, diagnosis, "
       "or treatment. Always consult qualified healthcare professionals.")
    _p(story, styles, "Supervisor: Komal Khawar — komal.khawer@vu.edu.pk")

    doc.build(story)
    print(f"PDF saved to: {OUT}")


if __name__ == "__main__":
    build_pdf()
