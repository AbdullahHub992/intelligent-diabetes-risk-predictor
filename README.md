# Intelligent Diabetes Risk Predictor

**CS619 Final Project** — Complete ML decision-support system for diabetes risk prediction.

## Complete Feature List

All 20 SRS functional requirements (FR-01–FR-20) are implemented:

1. User registration (Patient / Healthcare Provider) and Admin registration
2. User Login + Admin Login with RBAC
3. Password recovery, password change, profile management
4. Health data input and risk prediction (8 features + habits)
5. Prediction history, longitudinal tracking, dashboard
6. Risk factor explanation and personalized recommendations
7. PDF/CSV report export
8. Education resources
9. Clinical decision support (healthcare provider)
10. Feedback submission and model retraining
11. Dataset import, EDA, 70/30 preprocessing
12. Train/compare NN, SVM, DT, LR with model persistence
13. Account management (Admin)
14. Security: password hashing, RBAC, CSRF, HTTPS-ready

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

**Admin Panel**

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |

## Deploy to Render (free)

1. Push this project to GitHub.
2. Go to [render.com](render.com) → **New +** → **Blueprint** → select your repo.
3. Wait ~5–8 min for the first build. Your URL will be like `https://intelligent-diabetes-risk-predictor.onrender.com`.

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
