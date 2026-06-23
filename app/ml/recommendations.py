import json


def _add(category, priority, title, items, plan):
    plan["categories"].append({
        "category": category,
        "priority": priority,
        "title": title,
        "items": items,
    })


def generate_recommendation_plan(record, probability, risk_level, explanation=None):
    """Build a structured recommendation plan from prediction result and health data."""
    pct = round(probability * 100, 1)
    plan = {
        "risk_level": risk_level,
        "probability": pct,
        "summary": _summary(risk_level, pct),
        "categories": [],
    }

    if explanation and isinstance(explanation, str):
        try:
            explanation = json.loads(explanation)
        except json.JSONDecodeError:
            explanation = []

    _add("Medical Follow-up", "high", "What to do next", [
        "This system supports clinical decisions and does not replace professional medical advice.",
        "Consult a qualified healthcare provider for diagnosis and treatment.",
    ], plan)

    if risk_level == "Low":
        _add("Immediate Actions", "low", "Keep up the good work", [
            "Maintain your current healthy habits.",
            "Get a routine health checkup once a year.",
            f"Your diabetes probability is {pct}% — continue preventive care.",
        ], plan)
        _add("Lifestyle", "low", "Stay healthy", [
            "Eat balanced meals with vegetables, whole grains, and lean protein.",
            "Exercise at least 150 minutes per week (walking, cycling, swimming).",
            "Sleep 7–9 hours and manage stress.",
        ], plan)

    elif risk_level == "Moderate":
        _add("Immediate Actions", "medium", "Recommended within 2–4 weeks", [
            f"Your diabetes probability is {pct}% — moderate risk detected.",
            "Book an appointment with your doctor for review.",
            "Request a fasting blood sugar test and HbA1c test.",
            "Recheck your health values in 3 months.",
        ], plan)
        _add("Lifestyle", "medium", "Lifestyle changes to lower risk", [
            "Reduce sugary drinks, sweets, and white bread.",
            "Walk 30 minutes daily or 150 minutes per week.",
            "Monitor your weight and blood pressure weekly.",
            "Drink plenty of water and avoid late-night heavy meals.",
        ], plan)
        _add("Diet Plan", "medium", "Diet tips", [
            "Choose whole grains instead of refined flour (roti/brown rice).",
            "Fill half your plate with vegetables.",
            "Eat smaller portions and avoid overeating.",
        ], plan)

    else:  # High
        _add("Immediate Actions", "high", "Urgent — act soon", [
            f"Your diabetes probability is {pct}% — high risk detected.",
            "See a doctor within 1–2 weeks for proper evaluation.",
            "Get fasting glucose and HbA1c tests as soon as possible.",
            "Do not ignore symptoms: thirst, frequent urination, fatigue, blurred vision.",
        ], plan)
        _add("Lifestyle", "high", "Important lifestyle changes", [
            "Strictly limit sugar, soft drinks, and fried foods.",
            "Exercise daily if your doctor approves (start with 20–30 min walking).",
            "Monitor fasting blood sugar if you have a home glucometer.",
            "Track weight and blood pressure every week.",
        ], plan)
        _add("Diet Plan", "high", "Diet recommendations", [
            "Follow a low-sugar, high-fiber diet.",
            "Avoid fruit juice and packaged snacks.",
            "Ask your doctor about a referral to a dietitian.",
        ], plan)

    _personalized_from_record(record, plan)
    _personalized_from_factors(explanation, plan)

    plan["action_count"] = sum(len(c["items"]) for c in plan["categories"])
    return plan


def _summary(risk_level, pct):
    if risk_level == "Low":
        return f"Low risk ({pct}% diabetes probability). Continue healthy habits and regular checkups."
    if risk_level == "Moderate":
        return f"Moderate risk ({pct}% diabetes probability). Lifestyle changes and medical screening are recommended."
    return f"High risk ({pct}% diabetes probability). Please consult a doctor soon and follow the action plan below."


def _personalized_from_record(record, plan):
    items = []
    if record.glucose >= 140:
        items.append("Your fasting blood sugar is high — reduce sugar intake and retest soon.")
    elif record.glucose >= 100:
        items.append("Your fasting sugar is borderline — watch carbs and increase physical activity.")

    if record.bmi >= 30:
        items.append("Your BMI indicates obesity — aim for gradual weight loss (0.5–1 kg per week).")
    elif record.bmi >= 25:
        items.append("Your BMI is above normal — focus on portion control and daily exercise.")

    if getattr(record, "systolic", 0) >= 140 or record.ml_blood_pressure >= 90:
        items.append("Blood pressure is elevated — reduce salt, manage stress, and discuss with your doctor.")

    if record.age >= 45:
        items.append("Age 45+ increases diabetes risk — schedule regular screening tests.")

    if record.diabetes_pedigree >= 1:
        items.append("Family history of diabetes — stay extra vigilant with diet and checkups.")

    if record.insulin >= 200:
        items.append("Insulin level is high — may indicate insulin resistance; seek medical advice.")

    if record.sex == "female" and record.pregnancies >= 3:
        items.append("Multiple pregnancies — discuss gestational diabetes history with your doctor.")

    if items:
        _add("Personalized (based on your values)", "high", "Based on your health data", items, plan)


def _personalized_from_factors(explanation, plan):
    if not explanation:
        return
    items = []
    for factor in explanation[:3]:
        if factor.get("type") == "clinical_threshold":
            name = factor.get("factor", "Risk factor")
            items.append(f"{name} is a key concern — address this with your healthcare provider.")
    if items:
        _add("Risk Factors", "medium", "Top factors in your result", items, plan)


def plan_to_text(plan):
    lines = [plan["summary"], ""]
    for cat in plan["categories"]:
        lines.append(f"{cat['title']}:")
        for item in cat["items"]:
            lines.append(f"  • {item}")
        lines.append("")
    return "\n".join(lines).strip()


def parse_stored_recommendations(prediction):
    """Load plan from DB or rebuild plain-text legacy recommendations."""
    if not prediction or not prediction.recommendations:
        return None
    text = prediction.recommendations.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return {
        "summary": "Recommendations for your result",
        "risk_level": prediction.risk_level,
        "probability": round(prediction.probability * 100, 1),
        "categories": [{
            "category": "General",
            "priority": "medium",
            "title": "Recommendations",
            "items": [line.strip() for line in text.split("\n") if line.strip()],
        }],
    }
