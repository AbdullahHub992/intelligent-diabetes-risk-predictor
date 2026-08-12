# Intelligent Diabetes Risk Predictor

**CS619 Final Project** — Complete ML decision-support system for diabetes risk prediction.

## Complete Feature List

All 19 CS619 functional requirements implemented:

1. User Management & RBAC (Patient, Provider, Admin)
2. Health Data Input + Admin Dataset Import
3. EDA (summary stats, correlation, histograms, outcome distribution)
4. Data Preprocessing (cleaning, scaling, 70/30 split)
5. ML Models: Neural Network (MLP), SVM, Decision Tree, Logistic Regression
6. Evaluation: Accuracy, Precision, Recall, F1-score, Confusion Matrix (visual)
7. Model Comparison & Auto-Selection (F1) + Admin Override
8. Model Persistence (joblib)
9. ML-Based Risk Factor Analysis (feature importance + clinical thresholds)
10. Personalized Recommendations
11. Longitudinal Tracking with trend alerts
12. Role-Specific Dashboards with Chart.js
13. PDF & CSV Report Export (patient + provider)
14. Education Resources with Admin CMS
15. Clinical Decision Support + Provider Notes
16. Feedback & Model Retraining from verified outcomes
17. Admin Panel (users, training history, audit logs)
18. Performance (model caching, fast inference)
19. Security (password hash, CSRF, rate limiting, audit trail, consent)

## Quick Start

```bash
cd Intelligent_Diabetes_Risk_Predictor
pip install -r requirements.txt
python setup_data.py          # download dataset
python train_initial.py       # train models & generate plots
python run.py                 # start at http://localhost:5000
```

Or use Anaconda:
```bash
conda create -n diabetes python=3.12 -y
conda activate diabetes
pip install -r requirements.txt
python setup_data.py && python train_initial.py && python run.py
```

## Demo Accounts

**User Panel** (patients and healthcare providers log in via **User Login**)

| Type | Username | Password |
|------|----------|----------|
| Patient | patient | patient123 |
| Healthcare Provider | doctor | doctor123 |

**Admin Panel** (requires owner access code at login)

| Role | Username | Password | Owner Access Code |
|------|----------|----------|-------------------|
| Admin | admin | admin123 | `admin2026` |

Change the admin code via `.env` (`OWNER_ADMIN_ACCESS_CODE`) before deployment.

## Deploy to Render (free)

1. Push this project to GitHub.
2. Go to [render.com](https://render.com) → **New +** → **Blueprint** → select your repo.
3. Set env vars when prompted:
   - `OWNER_ADMIN_ACCESS_CODE` (e.g. your private admin code)
4. Wait ~5–8 min for the first build. Your URL will be like `https://intelligent-diabetes-risk-predictor.onrender.com`.

**Notes**
- Free tier sleeps after ~15 min idle; first visit after sleep takes ~30–60 s.
- Without `DATABASE_URL`, SQLite is used (data may reset on redeploy). For persistent data, add a free [Neon](https://neon.tech) Postgres URL as `DATABASE_URL`.

## Documentation

- [SRS](docs/SRS.md) — Full functional requirements (FR-01–FR-20) + traceability
- [User Manual](docs/USER_MANUAL.md) — Per-role guide
- [Test Plan](docs/TEST_PLAN.md) — Testing checklist

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Project Structure

```
├── app/
│   ├── ml/           # pipeline, predictor, explainability, retrain, reports
│   ├── routes/       # auth, main, admin, provider
│   ├── templates/    # all UI pages
│   └── static/plots/ # EDA & model charts
├── data/             # diabetes.csv dataset
├── saved_models/     # trained .joblib files
├── docs/             # SRS, manual, test plan
├── tests/            # unit tests
├── setup_data.py
├── train_initial.py
└── run.py
```

## Supervisor
Komal Khawer — komal.khawer@vu.edu.pk
