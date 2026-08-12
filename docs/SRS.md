# Software Requirements Specification
## Intelligent Diabetes Risk Predictor — CS619 (SRS v1.0)

**Group ID:** S26PROJECT0C0EB  
**Student:** Muhammad Shahmeer Akhtar (BC220415649)  
**Supervisor:** Komal Khawer  
**Date:** 25/05/2026

### 1. Introduction
Web-based ML decision-support system for diabetes risk prediction using clinical and lifestyle data. The system classifies an individual's risk level to assist patients and healthcare providers in early detection and preventive healthcare.

### 2. Scope
- **User (User Panel):** Patients and healthcare providers — login, health data input, predictions, dashboards, reports, education, clinical support
- **Admin (Admin Panel):** Dataset import, EDA, preprocessing (70/30 split), model training/comparison, persistence, user management, monitoring

### 2.1 Roles (SRS)
| Role | Description |
|------|-------------|
| **User** | Patient or healthcare provider — uses the User Panel |
| **Admin** | System administrator / student — uses the Admin Panel |

### 3. Functional Requirements

| ID | Requirement | Website Feature |
|----|-------------|-----------------|
| **FR-01** | User registration (Patient / Provider with credentials, security question, consent) | User Registration (`/register`) |
| **FR-02** | User login with RBAC (User Panel + Admin Panel) | User Login, Admin Login |
| **FR-03** | Password recovery (security questions or email) | Forgot Password |
| **FR-04** | Password change (current password required) | Change Password |
| **FR-05** | Profile management (contact info, baseline metrics) | My Profile |
| **FR-06** | Health data input & prediction (glucose, BP, BMI, age, habits, confidence) | Predict Risk → Generate Prediction |
| **FR-07** | Prediction history & longitudinal tracking | Prediction History, Longitudinal Tracking |
| **FR-08** | Risk factor analysis & explanation | Explain Result on prediction detail |
| **FR-09** | Personalized recommendations | Recommendations panel after prediction |
| **FR-10** | Dashboard & trend visualization | User Dashboard (Chart.js) |
| **FR-11** | Report export (PDF/CSV) | Export Report |
| **FR-12** | Education resources | Education + Admin CMS |
| **FR-13** | Clinical decision support | Provider Clinical panel |
| **FR-14** | Feedback submission | Feedback (patients and providers) |
| **FR-15** | Logout | Logout (all roles) |
| **FR-16** | Dataset ingestion (Admin) | Import Dataset |
| **FR-17** | EDA & preprocessing (70/30 split) | Perform EDA & Preprocessing |
| **FR-18** | Model training & comparison (NN, SVM, DT, LR) | Train & Compare Models |
| **FR-19** | Model persistence & retraining | joblib artifacts, Model Settings, Retrain from Feedback |
| **FR-20** | Account management (Admin) | Manage Users, Create User |

### 3.1 Functional Requirements Traceability (Implementation)

| ID | SRS Requirement | Implementation |
|----|-----------------|----------------|
| FR-01 | User registration (Patient / Provider) | `auth.register` — User role with profile subtype |
| FR-02 | User login with RBAC | `auth.user_login` (User) and `auth.login_admin` (Admin) |
| FR-03 | Password recovery | `auth.forgot_password` (security questions + email) |
| FR-04 | Password change | `auth.change_password` (current password required) |
| FR-05 | Profile management | `auth.profile_settings` (all roles) |
| FR-06 | Health data input & prediction | `main.health_data` — Generate Prediction |
| FR-07 | Prediction history & longitudinal tracking | `/my-health-records`, `/progress` |
| FR-08 | Risk factor analysis & explanation | `prediction_detail` — Explain Result |
| FR-09 | Personalized recommendations | `recommendations.py` |
| FR-10 | Dashboard & trend visualization | `dashboard.html`, Chart.js |
| FR-11 | Report export (PDF/CSV) | `export_report`, `export_pdf`, `export_csv` |
| FR-12 | Education resources | `education` + admin CMS |
| FR-13 | Clinical decision support | Provider routes |
| FR-14 | Feedback submission | `/feedback` |
| FR-15 | Logout | `auth.logout` |
| FR-16 | Dataset ingestion (Admin) | `admin.upload_dataset` |
| FR-17 | EDA & preprocessing (Admin) | `admin.eda`, 70/30 split |
| FR-18 | Model training & comparison | NN, SVM, DT, LR |
| FR-19 | Model persistence & retraining | joblib + `retrain.py` |
| FR-20 | Account management (Admin) | `admin.manage_users` |

### 4. Non-Functional Requirements
- **Performance:** Near real-time predictions (2–3 seconds)
- **Security:** Password hashing, RBAC, CSRF, HTTPS-ready, audit trail
- **Usability:** Responsive Bootstrap UI, color-coded risk indicators
- **Compatibility:** Cross-browser, mobile-responsive
- **Maintainability:** Modular ML pipeline separate from web backend

### 5. Use Cases
| ID | Use Case | Maps to |
|----|----------|---------|
| UC_01 | User Registration | FR-01 |
| UC_02 | User Login | FR-02 |
| UC_03 | Predict Risk | FR-06, FR-08, FR-09 |
| UC_04 | Track Progress | FR-07 |
| UC_05 | Export Report | FR-11 |
| UC_06 | Change Password | FR-04 |
| UC_07 | Logout | FR-15 |
| UC_08 | Admin Registration | Admin register flow |
| UC_09 | Admin Login | FR-02 |
| UC_10 | Import Dataset | FR-16 |
| UC_11 | Perform EDA | FR-17 |
| UC_12 | Train Models | FR-18 |

### 6. Dataset
Kaggle diabetic prediction / Pima Indians Diabetes — 8 features + Outcome.

### 7. Website SRS Compliance
The home page lists all FR-01–FR-20 requirements. Each major screen shows its FR badge via `app/srs_requirements.py`.
