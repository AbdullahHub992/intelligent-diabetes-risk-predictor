# Test Plan

## Unit Tests
Run: `python -m pytest tests/ -v`

| Test | Description |
|------|-------------|
| test_dataset_validation | CSV schema validation |
| test_clean_data | Zero glucose imputation |
| test_train_models | All 4 models train and persist |

## Manual Test Checklist

### Authentication
- [ ] Patient registration with consent
- [ ] Login rate limiting after 5 failures
- [ ] Role-based redirect (admin/provider/patient)
- [ ] Inactive user cannot login

### ML Pipeline
- [ ] Upload dataset with invalid columns → error
- [ ] Train models → 4 metrics + confusion matrix images
- [ ] Predict health data → risk level returned
- [ ] Retrain from feedback with actual outcomes

### Clinical
- [ ] Provider sees only assigned patients
- [ ] Clinical notes saved
- [ ] Provider exports patient PDF

### Security
- [ ] Audit log records login/prediction/export
- [ ] CSRF protection on forms
