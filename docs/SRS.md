# Software Requirements Specification
## Intelligent Diabetes Risk Predictor — CS619

### 1. Introduction
Web-based ML decision-support system for diabetes risk prediction using clinical and lifestyle data.

### 2. Functional Requirements Traceability

| ID | Requirement | Implementation |
|----|-------------|----------------|
| FR-01 | User registration & login | `auth.py`, RBAC roles |
| FR-02 | Role-based access control | `decorators.py`, role-specific routes |
| FR-03 | Health data input | `main.py` `/health-data` |
| FR-04 | Dataset import (admin) | `admin.py` `/upload-dataset` |
| FR-05 | EDA & visualization | `pipeline.py` `generate_eda()` |
| FR-06 | Data preprocessing | `clean_data()`, StandardScaler |
| FR-07 | 70/30 train-test split | `train_test_split(test_size=0.3)` |
| FR-08 | Neural Network model | MLPClassifier (64, 32) |
| FR-09 | SVM model | SVC (RBF kernel) |
| FR-10 | Decision Tree model | DecisionTreeClassifier |
| FR-11 | Logistic Regression | LogisticRegression |
| FR-12 | Evaluation metrics | Accuracy, Precision, Recall, F1 |
| FR-13 | Confusion matrix | Computed + heatmap PNG |
| FR-14 | Model comparison & selection | Auto F1 + admin override |
| FR-15 | Model persistence | joblib in `saved_models/` |
| FR-16 | Risk factor explanation | `explainability.py` |
| FR-17 | Personalized recommendations | `predictor.py` |
| FR-18 | Longitudinal tracking | `/progress`, Chart.js |
| FR-19 | Dashboard | Role-specific dashboards |
| FR-20 | PDF & CSV reports | `reports.py` |
| FR-21 | Education resources | `EducationResource` + admin CMS |
| FR-22 | Clinical decision support | Provider routes + notes |
| FR-23 | Feedback collection | `/feedback` |
| FR-24 | Model retraining from feedback | `retrain.py` |
| FR-25 | Admin model management | Admin panel |
| FR-26 | Security & audit | Password hash, audit logs, headers |

### 3. Non-Functional Requirements
- **Performance:** Model caching, single-record inference < 1s
- **Security:** CSRF, rate-limited login, audit trail, consent on registration
- **Usability:** Bootstrap responsive UI, role-based navigation

### 4. Dataset
Kaggle diabeticprediction / Pima Indians Diabetes — 8 features + Outcome.
