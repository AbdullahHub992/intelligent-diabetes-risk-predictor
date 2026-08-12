"""Generate Viva Questions & Answers PDF for CS619 project."""

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).resolve().parent / "docs" / "Viva_Questions_Answers.pdf"

SECTIONS = [
    ("Project Overview", [
        (
            "What is your project about?",
            "It is a web-based machine learning decision-support system that predicts diabetes risk "
            "from clinical and lifestyle data. Patients enter health metrics and get a risk score with "
            "explanations and recommendations. Doctors review assigned patients, and admins manage "
            "users, datasets, model training, and the system.",
        ),
        (
            "Why did you choose this topic?",
            "Diabetes is a growing global health problem, and early risk detection helps prevention. "
            "Machine learning can analyze multiple health factors together. A web app makes this "
            "accessible to patients and useful for doctors as a decision-support tool.",
        ),
        (
            "What problem does your system solve?",
            "It helps users understand their diabetes risk early, tracks health over time, explains "
            "which factors contribute most, and gives personalized recommendations. It also supports "
            "clinical workflows through doctor notes and admin oversight.",
        ),
        (
            "Is this a diagnostic system?",
            "No. It is a decision-support system. It estimates risk based on patterns in historical "
            "data. Final diagnosis must be done by a qualified doctor using proper clinical tests.",
        ),
    ]),
    ("Technology & Architecture", [
        (
            "Which technologies did you use and why?",
            "Python and Flask for the backend because they are lightweight and good for ML integration. "
            "SQLAlchemy handles the database. scikit-learn is used for ML. Bootstrap and Chart.js "
            "provide the UI. joblib saves trained models. Gunicorn and Docker are used for deployment on Render.",
        ),
        (
            "Explain your system architecture.",
            "It is a three-tier monolithic web application: Presentation layer (HTML templates, CSS, "
            "Chart.js), Application layer (Flask routes, forms, authentication, business logic), and "
            "Data/ML layer (database, dataset files, trained models, and ML pipeline).",
        ),
        (
            "What is the role of Flask blueprints in your project?",
            "Blueprints organize routes into modules: auth for login/register, main for patient features, "
            "admin for administration, and provider for doctor features. This keeps the code modular.",
        ),
        (
            "What is the application factory pattern?",
            "In create_app(), the Flask app is created and configured in one place—database, login manager, "
            "blueprints, migrations, and seed data. This makes testing and deployment easier.",
        ),
        (
            "How do you run the project locally?",
            "Install requirements, run setup_data.py to download the dataset, train_initial.py to train "
            "models, then run.py to start the server at http://localhost:5000.",
        ),
    ]),
    ("Database Design", [
        (
            "Which database do you use?",
            "SQLite for local development and PostgreSQL in production via DATABASE_URL on Render or Neon.",
        ),
        (
            "Name the main database tables.",
            "users, health_records, predictions, model_metrics, training_jobs, feedbacks, provider_patients, "
            "education_resources, clinical_notes, audit_logs, and report tables for admin-doctor-patient communication.",
        ),
        (
            "What is the relationship between HealthRecord and Prediction?",
            "Each health record stores patient vitals at a point in time. A prediction is generated from "
            "that record and stores the model output—probability, risk level, explanation, and recommendations.",
        ),
        (
            "What is the ProviderPatient table used for?",
            "It links doctors to their assigned patients so providers only see authorized patient data.",
        ),
    ]),
    ("User Roles & Features", [
        (
            "How many user roles are there?",
            "Three: Patient, Provider (Doctor), and Admin.",
        ),
        (
            "What can a patient do?",
            "Register/login, enter health data, view predictions, see recommendations, track progress, "
            "submit feedback, export PDF/CSV reports, read education content, and send reports to admin.",
        ),
        (
            "What can a doctor do?",
            "Login with owner access code, view assigned patients, review predictions, add clinical notes, "
            "use clinical decision support, export patient reports, and review cases forwarded by admin.",
        ),
        (
            "What can an admin do?",
            "Manage users, assign doctors to patients, upload datasets, view EDA, train/retrain models, "
            "set production model, manage education content, review feedback, and view audit logs.",
        ),
        (
            "What is RBAC?",
            "Role-Based Access Control means each user role has specific permissions. Routes are protected "
            "using role_required so patients cannot access admin pages and doctors only see assigned patients.",
        ),
    ]),
    ("Machine Learning", [
        (
            "Which dataset did you use?",
            "The Pima Indians Diabetes dataset. It has 8 input features and a binary outcome (diabetic or not).",
        ),
        (
            "What are the 8 features?",
            "Pregnancies, Glucose, Blood Pressure, Skin Thickness, Insulin, BMI, Diabetes Pedigree Function, and Age.",
        ),
        (
            "Which ML models did you implement?",
            "Neural Network (MLP), SVM, Decision Tree, and Logistic Regression.",
        ),
        (
            "Why use multiple models?",
            "Different algorithms behave differently on the same data. Comparing them helps select the most reliable model.",
        ),
        (
            "How do you preprocess the data?",
            "Zero values in certain columns are treated as missing. Missing values are imputed with median. "
            "Features are scaled using StandardScaler. Data is split 70% train and 30% test.",
        ),
        (
            "What is your ML pipeline?",
            "Imputer, then Scaler, then Classifier—built as a scikit-learn Pipeline for consistent training and inference.",
        ),
        (
            "How do you evaluate models?",
            "Using Accuracy, Precision, Recall, F1-score, confusion matrix, and ROC-AUC.",
        ),
        (
            "Which metric selects the best model?",
            "F1-score, because it balances precision and recall on imbalanced data.",
        ),
        (
            "Can admin override the best model?",
            "Yes. Admin can manually set the production model from Model Settings.",
        ),
        (
            "How is prediction done for a new patient?",
            "Health form data is converted to the same feature format as training, passed through the saved "
            "pipeline, and predict_proba gives the diabetes probability.",
        ),
        (
            "How do you define risk levels?",
            "Low: below 35%. Moderate: 35% to 65%. High: above 65%.",
        ),
        (
            "How does explainability work?",
            "Two methods: ML feature importance from model coefficients or tree importances, and clinical "
            "threshold checks such as glucose above 140 or BMI above 30.",
        ),
        (
            "How are recommendations generated?",
            "Based on risk level, probability, and explanation factors—for example diet advice for high BMI.",
        ),
        (
            "How do you save and load models?",
            "Trained pipelines are saved using joblib in saved_models/ and loaded at prediction time with in-memory caching.",
        ),
        (
            "What is model retraining?",
            "When patients submit feedback with actual outcomes, admin can retrain using the original dataset "
            "plus verified feedback rows.",
        ),
        (
            "Why is blood pressure converted before prediction?",
            "The UI collects systolic and diastolic separately, but the dataset uses one BloodPressure feature. "
            "The system computes mean arterial pressure: (2 x systolic + diastolic) / 3.",
        ),
    ]),
    ("Security", [
        (
            "How are passwords stored?",
            "Passwords are hashed using Werkzeug generate_password_hash, not stored in plain text.",
        ),
        (
            "What is CSRF protection?",
            "Flask-WTF adds CSRF tokens to forms so malicious sites cannot submit fake requests.",
        ),
        (
            "What is the owner access code?",
            "An extra security layer for admin and doctor login beyond username and password.",
        ),
        (
            "How do you prevent brute-force login?",
            "Rate limiting allows only 5 failed login attempts per IP and username within 5 minutes.",
        ),
        (
            "What is an audit log?",
            "A record of important actions with user, action, timestamp, and IP address for accountability.",
        ),
    ]),
    ("Testing & Deployment", [
        (
            "How did you test the project?",
            "Using pytest unit tests in the tests/ folder and a manual test plan in docs/TEST_PLAN.md.",
        ),
        (
            "How is the app deployed?",
            "Using Docker and Render. render.yaml defines the web service. Gunicorn serves the Flask app.",
        ),
        (
            "What happens on Render free tier?",
            "The app sleeps after about 15 minutes of inactivity. First visit after sleep may take 30–60 seconds.",
        ),
        (
            "Why use PostgreSQL in production?",
            "SQLite data on Render can be lost on redeploy. PostgreSQL gives persistent storage.",
        ),
    ]),
    ("EDA & Reports", [
        (
            "What is EDA in your project?",
            "Exploratory Data Analysis—summary statistics, correlation heatmap, histograms, and outcome distribution plots.",
        ),
        (
            "What reports can users export?",
            "Patients export PDF and CSV reports. Doctors export reports for assigned patients. Admin can export EDA as PDF.",
        ),
        (
            "What is longitudinal tracking?",
            "The progress page shows how a patient's risk and health metrics change over multiple health record entries.",
        ),
    ]),
    ("Common Technical Questions", [
        (
            "What is Flask-Login?",
            "A Flask extension that manages user sessions—login, logout, and current_user across requests.",
        ),
        (
            "What is WTForms used for?",
            "Form creation and server-side validation before saving data or running prediction.",
        ),
        (
            "What is a confusion matrix?",
            "A table showing True Positives, True Negatives, False Positives, and False Negatives.",
        ),
        (
            "Difference between precision and recall?",
            "Precision: of predicted positives, how many were correct. Recall: of actual positives, how many the model found.",
        ),
        (
            "Why use StandardScaler?",
            "Features like age and glucose have different scales. Scaling helps SVM and Neural Networks perform better.",
        ),
        (
            "What is overfitting?",
            "When a model learns training data too closely and performs poorly on new data. Reduced using train-test split and early stopping.",
        ),
        (
            "What is joblib?",
            "A Python library to serialize and load scikit-learn models efficiently.",
        ),
        (
            "What is Gunicorn?",
            "A production WSGI server that runs the Flask app, unlike Flask's built-in development server.",
        ),
    ]),
    ("Limitations & Future Work", [
        (
            "What are the limitations of your project?",
            "Based on a small specific dataset, only 8 features, not a medical diagnosis tool, free hosting has delays, "
            "and no mobile app or EHR integration yet.",
        ),
        (
            "How can you improve the project?",
            "Use larger datasets, add SHAP/LIME explainability, integrate with hospital systems, add alerts, "
            "implement MFA for staff, and use paid hosting.",
        ),
        (
            "How is your project different from a simple ML script?",
            "It is a complete system with user roles, database, security, explainability, recommendations, "
            "progress tracking, admin model management, feedback retraining, and deployment.",
        ),
    ]),
    ("Quick Revision", [
        (
            "Summarize the project in one minute.",
            "Intelligent Diabetes Risk Predictor is a Flask web app with scikit-learn ML. It uses the Pima Indians "
            "dataset with 4 models (MLP, SVM, Decision Tree, Logistic Regression). Best model is selected by F1-score. "
            "Three roles: Patient, Doctor, Admin. Security includes hashing, CSRF, RBAC, rate limiting, and audit logs. "
            "Deployed on Render with Docker. It is decision support, not a diagnosis tool.",
        ),
    ]),
]


def build_pdf():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=10,
        textColor=colors.HexColor("#1565C0"),
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=12,
        textColor=colors.grey,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=16,
        spaceAfter=10,
        textColor=colors.HexColor("#0D47A1"),
    )
    question_style = ParagraphStyle(
        "Question",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceBefore=8,
        spaceAfter=2,
        textColor=colors.HexColor("#1565C0"),
        fontName="Helvetica-Bold",
    )
    answer_style = ParagraphStyle(
        "Answer",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
        leftIndent=12,
    )

    story = []
    story.append(Paragraph("Viva Questions &amp; Answers", title_style))
    story.append(Paragraph("Intelligent Diabetes Risk Predictor — CS619 Final Project", subtitle_style))
    story.append(Paragraph(f"Prepared: {date.today().strftime('%B %d, %Y')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1565C0")))
    story.append(Spacer(1, 0.1 * inch))

    q_num = 1
    for section_title, items in SECTIONS:
        story.append(Paragraph(section_title, section_style))
        for question, answer in items:
            story.append(Paragraph(f"Q{q_num}. {question}", question_style))
            story.append(Paragraph(f"A: {answer}", answer_style))
            q_num += 1

    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Paragraph(
        "Supervisor: Komal Khawer — komal.khawer@vu.edu.pk",
        subtitle_style,
    ))

    doc.build(story)
    print(f"PDF saved to: {OUT}")


if __name__ == "__main__":
    build_pdf()
