# Test Plan

## Unit Tests
Run: `python -m pytest tests/ -v`

## Manual Test Checklist (SRS / Design Document)

### User Panel
- [ ] UC_01 User registration as Patient or Healthcare Provider (credentials only)
- [ ] UC_02 User login with valid credentials; invalid login is rejected
- [ ] FR-03 Password recovery with registered username/email; unknown identity is rejected
- [ ] UC_06 Change password (current password required)
- [ ] FR-05 View and update profile
- [ ] UC_03 Predict Risk with eight clinical features + habits; out-of-range values rejected
- [ ] FR-08 Explain Result and FR-09 recommendations shown
- [ ] UC_04 Prediction history / longitudinal tracking
- [ ] FR-10 User Dashboard trends
- [ ] UC_05 Export PDF / CSV
- [ ] FR-12 Education resources displayed
- [ ] FR-13 Clinical decision support for healthcare providers
- [ ] FR-14 Submit feedback
- [ ] UC_07 Logout

### Admin Panel
- [ ] UC_08 Admin registration (credentials only)
- [ ] UC_09 Admin login with username and password
- [ ] UC_10 Import valid dataset; invalid columns rejected
- [ ] UC_11 EDA and 70/30 preprocessing
- [ ] UC_12 Train and compare NN, SVM, DT, LR
- [ ] FR-19 Model persistence / retraining / model settings
- [ ] FR-20 Account Management (Admin): create/edit users; duplicate identity rejected

### Security
- [ ] Password is hashed
- [ ] RBAC: User Panel vs Admin Panel
- [ ] CSRF protection on forms
