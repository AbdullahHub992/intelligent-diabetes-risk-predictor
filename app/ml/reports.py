import csv
import io
import json
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.ml.recommendations import parse_stored_recommendations, plan_to_text


def _recommendations_export_text(prediction):
    plan = parse_stored_recommendations(prediction)
    if plan:
        return plan_to_text(plan)
    return prediction.recommendations or ""


def generate_csv_report(user, predictions, health_records):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Report Date", "Patient", "Record Date", "Sex", "Pregnancies", "Fasting Sugar",
        "Systolic BP", "Diastolic BP",
        "Skin Thickness", "Insulin", "BMI", "Pedigree", "Age",
        "Model", "Probability", "Risk Level", "Risk Factors", "Recommendations",
    ])
    record_map = {r.id: r for r in health_records}
    for p in predictions:
        record = record_map.get(p.health_record_id)
        factors = ""
        if p.explanation:
            try:
                exp = json.loads(p.explanation)
                factors = " | ".join(f"{e.get('factor')}: {e.get('message', '')}" for e in exp[:3])
            except json.JSONDecodeError:
                factors = p.explanation
        writer.writerow([
            datetime.utcnow().strftime("%Y-%m-%d"), user.full_name,
            record.recorded_at.strftime("%Y-%m-%d") if record else "",
            record.sex if record else "",
            record.pregnancies if record else "",
            record.glucose if record else "",
            record.systolic if record else "",
            record.diastolic if record else "",
            record.skin_thickness if record else "",
            record.insulin if record else "",
            record.bmi if record else "",
            record.diabetes_pedigree if record else "",
            record.age if record else "",
            p.model_name, f"{p.probability:.2%}", p.risk_level,
            factors,
            _recommendations_export_text(p).replace("\n", " | "),
        ])
    return output.getvalue()


def generate_pdf_report(user, predictions, health_records, metrics):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Intelligent Diabetes Risk Predictor - Health Report</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Patient: {user.full_name}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Spacer(1, 16))

    if predictions:
        story.append(Paragraph("<b>Prediction Results</b>", styles["Heading2"]))
        pred_data = [["Date", "Model", "Probability", "Risk Level"]]
        record_map = {r.id: r for r in health_records}
        for p in predictions:
            record = record_map.get(p.health_record_id)
            date_str = record.recorded_at.strftime("%Y-%m-%d") if record else p.created_at.strftime("%Y-%m-%d")
            pred_data.append([date_str, p.model_name, f"{p.probability:.2%}", p.risk_level])
        table = Table(pred_data, colWidths=[90, 120, 90, 90])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 16))

        latest = predictions[0]
        if latest.explanation:
            story.append(Paragraph("<b>Risk Factor Analysis</b>", styles["Heading2"]))
            try:
                for item in json.loads(latest.explanation)[:5]:
                    story.append(Paragraph(
                        f"• <b>{item.get('factor')}</b>: {item.get('message', '')}",
                        styles["Normal"],
                    ))
            except json.JSONDecodeError:
                pass
            story.append(Spacer(1, 12))

        story.append(Paragraph("<b>Personalized Recommendations</b>", styles["Heading2"]))
        rec_plan = parse_stored_recommendations(latest)
        if rec_plan:
            story.append(Paragraph(rec_plan.get("summary", ""), styles["Normal"]))
            story.append(Spacer(1, 8))
            for block in rec_plan.get("categories", []):
                story.append(Paragraph(f"<b>{block.get('title', 'Recommendations')}</b>", styles["Heading3"]))
                for item in block.get("items", []):
                    story.append(Paragraph(f"• {item}", styles["Normal"]))
                story.append(Spacer(1, 6))
        else:
            for line in (latest.recommendations or "").split("\n"):
                story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 16))

    if metrics:
        story.append(Paragraph("<b>Model Evaluation Metrics</b>", styles["Heading2"]))
        metric_data = [["Model", "Accuracy", "Precision", "Recall", "F1", "Best"]]
        for m in metrics:
            metric_data.append([
                m.model_name, f"{m.accuracy:.2%}", f"{m.precision:.2%}",
                f"{m.recall:.2%}", f"{m.f1_score:.2%}", "Yes" if m.is_best else "No",
            ])
        mtable = Table(metric_data)
        mtable.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#059669")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(mtable)

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "<i>Decision support only — not a substitute for professional medical advice.</i>",
        styles["Italic"],
    ))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_eda_pdf(eda_results, dataset_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>Exploratory Data Analysis Report</b>", styles["Title"]),
        Paragraph(f"Dataset: {dataset_name}", styles["Normal"]),
        Spacer(1, 16),
        Paragraph("<b>Summary Statistics</b>", styles["Heading2"]),
    ]
    data = [["Feature", "Mean", "Std", "Min", "Max"]]
    for feature, stats in eda_results["summary"].items():
        data.append([
            feature, f"{stats['mean']:.2f}", f"{stats['std']:.2f}",
            f"{stats['min']:.2f}", f"{stats['max']:.2f}",
        ])
    table = Table(data)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer
