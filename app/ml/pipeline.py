import json
import os

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

FEATURE_COLUMNS = [
    "Pregnancies",
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
    "DiabetesPedigreeFunction",
    "Age",
]
TARGET_COLUMN = "Outcome"
ZERO_COLS = ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"]

MODEL_BUILDERS = {
    "Neural Network": lambda: MLPClassifier(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        max_iter=800,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=20,
        random_state=42,
    ),
    "SVM": lambda: SVC(
        kernel="rbf", probability=True, random_state=42, class_weight="balanced",
    ),
    "Decision Tree": lambda: DecisionTreeClassifier(
        max_depth=5, random_state=42, class_weight="balanced",
    ),
    "Logistic Regression": lambda: LogisticRegression(
        max_iter=2000, random_state=42, class_weight="balanced",
    ),
}


def record_to_frame(record):
    """Build a single-row feature frame; 0 = missing (same rule as training)."""
    frame = pd.DataFrame([{
        "Pregnancies": record.pregnancies,
        "Glucose": record.glucose,
        "BloodPressure": record.ml_blood_pressure,
        "SkinThickness": record.skin_thickness,
        "Insulin": record.insulin,
        "BMI": record.bmi,
        "DiabetesPedigreeFunction": record.diabetes_pedigree,
        "Age": record.age,
    }])
    for col in ZERO_COLS:
        frame[col] = frame[col].replace(0, np.nan)
    return frame


def _training_frame(df):
    """Prepare feature matrix for training (zeros become NaN for the imputer)."""
    out = df.copy()
    for col in FEATURE_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ZERO_COLS:
        out[col] = out[col].replace(0, np.nan)
    if TARGET_COLUMN in out.columns:
        out[TARGET_COLUMN] = out[TARGET_COLUMN].fillna(0).astype(int)
    return out


def build_model_pipeline(builder):
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("clf", builder()),
    ])


def load_dataset(filepath):
    df = pd.read_csv(filepath)
    df.columns = [c.strip() for c in df.columns]
    rename_map = {
        "Blood Pressure": "BloodPressure",
        "Skin Thickness": "SkinThickness",
        "Diabetes Pedigree Function": "DiabetesPedigreeFunction",
    }
    df = df.rename(columns=rename_map)
    return df


def clean_data(df):
    df = df.copy()
    for col in FEATURE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if col in ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"]:
                df[col] = df[col].replace(0, np.nan)
                df[col] = df[col].fillna(df[col].median())
    if TARGET_COLUMN in df.columns:
        df[TARGET_COLUMN] = df[TARGET_COLUMN].fillna(0).astype(int)
    df = df.dropna(subset=FEATURE_COLUMNS)
    return df


def generate_eda(df, plot_folder):
    os.makedirs(plot_folder, exist_ok=True)
    summary = df[FEATURE_COLUMNS + [TARGET_COLUMN]].describe().to_dict()

    plt.figure(figsize=(10, 6))
    sns.heatmap(df[FEATURE_COLUMNS + [TARGET_COLUMN]].corr(), annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("Feature Correlation Heatmap")
    plt.tight_layout()
    corr_path = os.path.join(plot_folder, "correlation_heatmap.png")
    plt.savefig(corr_path)
    plt.close()

    plt.figure(figsize=(12, 8))
    df[FEATURE_COLUMNS].hist(bins=20, figsize=(12, 8))
    plt.suptitle("Feature Distributions")
    plt.tight_layout()
    hist_path = os.path.join(plot_folder, "feature_histograms.png")
    plt.savefig(hist_path)
    plt.close()

    plt.figure(figsize=(8, 5))
    sns.countplot(x=TARGET_COLUMN, data=df, hue=TARGET_COLUMN, palette="Set2", legend=False)
    plt.title("Diabetes Outcome Distribution")
    plt.tight_layout()
    outcome_path = os.path.join(plot_folder, "outcome_distribution.png")
    plt.savefig(outcome_path)
    plt.close()

    return {
        "summary": summary,
        "plots": {
            "correlation": "plots/correlation_heatmap.png",
            "histograms": "plots/feature_histograms.png",
            "outcome": "plots/outcome_distribution.png",
        },
    }


def train_all_models(df, model_folder, test_size=0.3, random_state=42):
    os.makedirs(model_folder, exist_ok=True)
    df = _training_frame(df)
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN].astype(int).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    results = []
    best_auc = -1.0
    best_model_name = None
    production_name = (
        "Logistic Regression"
        if "Logistic Regression" in MODEL_BUILDERS
        else list(MODEL_BUILDERS.keys())[0]
    )

    for name, builder in MODEL_BUILDERS.items():
        pipe = build_model_pipeline(builder)
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        y_proba = pipe.predict_proba(X_test)[:, 1]

        cm = confusion_matrix(y_test, y_pred)
        cm_plot = _plot_confusion_matrix(cm, name, model_folder)
        metrics = {
            "model_name": name,
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_proba)),
            "confusion_matrix": cm.tolist(),
            "confusion_matrix_plot": cm_plot,
        }
        results.append(metrics)

        safe_name = name.lower().replace(" ", "_")
        joblib.dump(pipe, os.path.join(model_folder, f"{safe_name}.joblib"))

        if metrics["roc_auc"] > best_auc:
            best_auc = metrics["roc_auc"]
            best_model_name = name

    for r in results:
        r["is_best"] = r["model_name"] == best_model_name

    # Production pipeline: logistic regression re-fit on all rows.
    production_pipe = build_model_pipeline(MODEL_BUILDERS[production_name])
    production_pipe.fit(X, y)
    joblib.dump(production_pipe, os.path.join(model_folder, "production_pipeline.joblib"))

    # Legacy scaler for older code paths (extracted from production pipe).
    joblib.dump(production_pipe.named_steps["scaler"], os.path.join(model_folder, "scaler.joblib"))

    joblib.dump(best_model_name, os.path.join(model_folder, "best_model.joblib"))
    joblib.dump(production_name, os.path.join(model_folder, "production_model.joblib"))
    joblib.dump(FEATURE_COLUMNS, os.path.join(model_folder, "features.joblib"))

    comparison_path = os.path.join(model_folder, "model_comparison.json")
    with open(comparison_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    _plot_model_comparison(results, model_folder)

    return results, best_model_name


def _plot_confusion_matrix(cm, model_name, model_folder):
    plot_folder = os.path.join(os.path.dirname(model_folder), "app", "static", "plots")
    os.makedirs(plot_folder, exist_ok=True)
    safe = model_name.lower().replace(" ", "_")
    path = os.path.join(plot_folder, f"cm_{safe}.png")

    plt.figure(figsize=(5, 4))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=["No Diabetes", "Diabetes"],
        yticklabels=["No Diabetes", "Diabetes"],
    )
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title(f"Confusion Matrix - {model_name}")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return f"plots/cm_{safe}.png"


def _plot_model_comparison(results, model_folder):
    plot_folder = os.path.join(os.path.dirname(model_folder), "app", "static", "plots")
    os.makedirs(plot_folder, exist_ok=True)

    names = [r["model_name"] for r in results]
    metrics = ["accuracy", "precision", "recall", "f1_score"]
    x = np.arange(len(names))
    width = 0.2

    plt.figure(figsize=(12, 6))
    for i, metric in enumerate(metrics):
        values = [r[metric] for r in results]
        plt.bar(x + i * width, values, width, label=metric.replace("_", " ").title())

    plt.xlabel("Model")
    plt.ylabel("Score")
    plt.title("Model Performance Comparison")
    plt.xticks(x + width * 1.5, names, rotation=15)
    plt.ylim(0, 1.05)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(plot_folder, "model_comparison.png"))
    plt.close()


def get_best_model_name(model_folder):
    path = os.path.join(model_folder, "best_model.joblib")
    if os.path.exists(path):
        return joblib.load(path)
    return None


def load_model(model_name, model_folder):
    safe_name = model_name.lower().replace(" ", "_")
    path = os.path.join(model_folder, f"{safe_name}.joblib")
    if os.path.exists(path):
        return joblib.load(path)
    return None


def load_production_pipeline(model_folder):
    path = os.path.join(model_folder, "production_pipeline.joblib")
    if os.path.exists(path):
        return joblib.load(path)
    return load_model("Logistic Regression", model_folder)


def load_scaler(model_folder):
    path = os.path.join(model_folder, "scaler.joblib")
    if not os.path.exists(path):
        return None
    return joblib.load(path)
