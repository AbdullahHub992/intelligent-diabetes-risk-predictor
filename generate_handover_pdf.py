"""Generate a PDF handover document for stakeholders / supervisors."""

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent / "docs" / "Intelligent_Diabetes_Risk_Predictor_Handover.pdf"
LIVE_URL = "https://intelligent-diabetes-risk-predictor.onrender.com"
GITHUB = "https://github.com/AbdullahHub992/intelligent-diabetes-risk-predictor"


def build_pdf():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=14,
        textColor=colors.HexColor("#1565C0"),
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#0D47A1"),
    )
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=11, leading=15, spaceAfter=6)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.grey)

    story = []

    story.append(Paragraph("Intelligent Diabetes Risk Predictor", title))
    story.append(Paragraph("CS619 Final Project — Project Handover Document", body))
    story.append(Paragraph(f"Prepared: {date.today().strftime('%B %d, %Y')}", small))
    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1565C0")))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("1. About This System", h2))
    story.append(Paragraph(
        "This web application is an intelligent decision-support system for estimating "
        "diabetes risk using machine learning. It supports three roles: <b>Patient</b>, "
        "<b>Healthcare Provider (Doctor)</b>, and <b>Administrator</b>. "
        "The system provides risk prediction, personalized recommendations, progress tracking, "
        "education resources, clinical decision support, and report export (PDF/CSV).",
        body,
    ))
    story.append(Paragraph(
        "<b>Important:</b> This tool is for educational and decision-support purposes only. "
        "It is <b>not</b> a medical diagnosis. Users should consult qualified healthcare "
        "professionals for clinical decisions.",
        body,
    ))

    story.append(Paragraph("2. Live Website", h2))
    story.append(Paragraph(f"<b>Main URL:</b> <link href='{LIVE_URL}' color='blue'>{LIVE_URL}</link>", body))
    story.append(Paragraph(f"<b>Health check:</b> {LIVE_URL}/health", body))
    story.append(Paragraph(
        "Note: On the free hosting plan, the site may sleep after inactivity. "
        "The first visit after sleep can take 30–60 seconds to load.",
        small,
    ))

    story.append(Paragraph("3. Login Pages & Demo Accounts", h2))
    login_data = [
        ["Role", "Login URL", "Username", "Password", "Owner Access Code"],
        ["Patient", f"{LIVE_URL}/login/patient", "patient", "patient123", "—"],
        ["Doctor", f"{LIVE_URL}/login/doctor", "doctor", "doctor123", "doctor2026"],
        ["Admin", f"{LIVE_URL}/login/admin", "admin", "admin123", "admin2026"],
    ]
    t = Table(login_data, colWidths=[0.75 * inch, 2.1 * inch, 0.85 * inch, 0.95 * inch, 1.15 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E3F2FD")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        "Admin and Doctor logins require the <b>owner access code</b> in addition to username and password. "
        "Use the admin code only on the admin login page and the doctor code only on the doctor login page.",
        small,
    ))

    story.append(Paragraph("4. How to Use (By Role)", h2))

    story.append(Paragraph("<b>Patient</b>", body))
    for step in [
        "Register or log in with the patient account.",
        "Open <b>Health Data</b> and enter health measurements.",
        "View your diabetes risk prediction, explanations, and recommendations.",
        "Track progress over time on the <b>Progress</b> page.",
        "Read prevention tips under <b>Education</b>.",
        "Submit feedback and export PDF/CSV reports from the dashboard.",
    ]:
        story.append(Paragraph(f"• {step}", body))

    story.append(Paragraph("<b>Healthcare Provider (Doctor)</b>", body))
    for step in [
        "Log in at the doctor portal with owner access code.",
        "View assigned patients and high-risk cases on the clinical dashboard.",
        "Review patient records, predictions, and charts.",
        "Use <b>Clinical Support</b> for ML risk analysis and add clinical notes.",
        "Export patient reports and submit feedback on predictions.",
    ]:
        story.append(Paragraph(f"• {step}", body))

    story.append(Paragraph("<b>Administrator</b>", body))
    for step in [
        "Log in at the admin portal with owner access code.",
        "Upload datasets, run EDA, and train ML models (Neural Network, SVM, Decision Tree, Logistic Regression).",
        "Compare models and set the production model.",
        "Manage users, provider–patient assignments, and education content.",
        "Review feedback, audit logs, and retrain models from verified outcomes.",
    ]:
        story.append(Paragraph(f"• {step}", body))

    story.append(Paragraph("5. Key Features Implemented", h2))
    features = [
        "User management with role-based access control (Patient, Provider, Admin)",
        "Health data input and ML-based diabetes risk prediction",
        "Exploratory data analysis and model training pipeline",
        "Four ML algorithms with comparison and auto-selection",
        "Personalized recommendations and risk factor explanation",
        "Longitudinal tracking with trend alerts",
        "PDF and CSV report export",
        "Education resource management",
        "Clinical decision support and provider notes",
        "Security: password hashing, CSRF protection, rate limiting, audit trail",
    ]
    for f in features:
        story.append(Paragraph(f"• {f}", body))

    story.append(Paragraph("6. Technical Information", h2))
    tech_data = [
        ["Item", "Details"],
        ["Technology", "Python, Flask, SQLAlchemy, scikit-learn, ReportLab, Chart.js"],
        ["ML Models", "Neural Network (MLP), SVM, Decision Tree, Logistic Regression"],
        ["Dataset", "Pima Indians Diabetes Dataset (UCI)"],
        ["Hosting", "Render (Docker)"],
        ["Source Code", GITHUB],
        ["Supervisor", "Komal Khawer — komal.khawer@vu.edu.pk"],
    ]
    t2 = Table(tech_data, colWidths=[1.4 * inch, 4.6 * inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E3F2FD")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)

    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        "Disclaimer: This application provides an educational risk estimate based on statistical "
        "models trained on a public dataset. It does not replace professional medical advice, "
        "diagnosis, or treatment.",
        small,
    ))

    doc.build(story)
    print(f"PDF saved to: {OUT}")


if __name__ == "__main__":
    build_pdf()
