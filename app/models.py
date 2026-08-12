from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="patient")
    professional_credentials = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    baseline_height_cm = db.Column(db.Float, nullable=True)
    baseline_weight_kg = db.Column(db.Float, nullable=True)
    baseline_age = db.Column(db.Integer, nullable=True)
    baseline_sex = db.Column(db.String(10), nullable=True)
    security_question = db.Column(db.String(200), nullable=True)
    security_answer_hash = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    health_records = db.relationship("HealthRecord", backref="user", lazy=True)
    predictions = db.relationship("Prediction", backref="user", lazy=True)
    feedbacks = db.relationship("Feedback", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_security_answer(self, answer):
        self.security_answer_hash = generate_password_hash(answer.strip().lower())

    def check_security_answer(self, answer):
        if not self.security_answer_hash:
            return False
        return check_password_hash(self.security_answer_hash, answer.strip().lower())

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_provider(self):
        return self.role == "provider"

    @property
    def is_patient(self):
        return self.role == "patient"

    @property
    def is_user(self):
        """SRS User role: patient or healthcare provider."""
        return self.role in ("patient", "provider")


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(db.String(256), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="reset_tokens")


class ProviderPatient(db.Model):
    __tablename__ = "provider_patients"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider = db.relationship("User", foreign_keys=[provider_id], backref="assigned_patients")
    patient = db.relationship("User", foreign_keys=[patient_id], backref="care_providers")


class HealthRecord(db.Model):
    __tablename__ = "health_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sex = db.Column(db.String(10), nullable=False, default="female")
    pregnancies = db.Column(db.Integer, default=0)
    glucose = db.Column(db.Float, nullable=False)
    systolic = db.Column(db.Float, nullable=False, default=120)
    diastolic = db.Column(db.Float, nullable=False, default=80)
    blood_pressure = db.Column(db.Float, nullable=True)  # legacy; diastolic used for ML
    skin_thickness = db.Column(db.Float, nullable=False)
    insulin = db.Column(db.Float, nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    diabetes_pedigree = db.Column(db.Float, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    smoking = db.Column(db.String(20), nullable=True)
    physical_activity = db.Column(db.String(30), nullable=True)
    diet_quality = db.Column(db.String(30), nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    prediction = db.relationship("Prediction", backref="health_record", uselist=False)

    @property
    def ml_blood_pressure(self):
        """MAP from systolic/diastolic so both BP values affect the model."""
        dia = self.diastolic if self.diastolic is not None else (self.blood_pressure or 80)
        sys = getattr(self, "systolic", None)
        if sys is not None and sys > dia:
            return (2.0 * sys + dia) / 3.0
        return dia


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    health_record_id = db.Column(db.Integer, db.ForeignKey("health_records.id"), nullable=False)
    model_name = db.Column(db.String(50), nullable=False)
    probability = db.Column(db.Float, nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(20), nullable=False)
    explanation = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ModelMetrics(db.Model):
    __tablename__ = "model_metrics"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(50), nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    precision = db.Column(db.Float, nullable=False)
    recall = db.Column(db.Float, nullable=False)
    f1_score = db.Column(db.Float, nullable=False)
    confusion_matrix = db.Column(db.Text)
    confusion_matrix_plot = db.Column(db.String(255))
    is_best = db.Column(db.Boolean, default=False)
    trained_at = db.Column(db.DateTime, default=datetime.utcnow)
    training_job_id = db.Column(db.Integer, db.ForeignKey("training_jobs.id"))


class TrainingJob(db.Model):
    __tablename__ = "training_jobs"

    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(50), nullable=False)
    dataset_filename = db.Column(db.String(255))
    rows_used = db.Column(db.Integer, default=0)
    feedback_rows = db.Column(db.Integer, default=0)
    best_model = db.Column(db.String(50))
    status = db.Column(db.String(20), default="completed")
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    metrics = db.relationship("ModelMetrics", backref="training_job", lazy=True)


class Dataset(db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    rows = db.Column(db.Integer, default=0)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class Feedback(db.Model):
    __tablename__ = "feedbacks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"))
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    actual_outcome = db.Column(db.Integer)
    used_in_training = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    prediction = db.relationship("Prediction", backref="feedbacks")


class EducationResource(db.Model):
    __tablename__ = "education_resources"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    external_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ClinicalNote(db.Model):
    __tablename__ = "clinical_notes"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"))
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider = db.relationship("User", foreign_keys=[provider_id])
    patient = db.relationship("User", foreign_keys=[patient_id])


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(100), nullable=False)
    resource = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="audit_logs")


class SystemConfig(db.Model):
    __tablename__ = "system_config"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)


class AdminReportSubmission(db.Model):
    __tablename__ = "admin_report_submissions"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"), nullable=False)
    message = db.Column(db.Text)
    report_summary = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("User", foreign_keys=[patient_id], backref="admin_report_submissions")
    prediction = db.relationship("Prediction", backref="admin_report_submissions")
    doctor_forwards = db.relationship("DoctorReportForward", backref="admin_report", lazy=True)


class DoctorReportForward(db.Model):
    __tablename__ = "doctor_report_forwards"
    __table_args__ = (
        db.UniqueConstraint("admin_report_id", "provider_id", name="uq_report_doctor_forward"),
    )

    id = db.Column(db.Integer, primary_key=True)
    admin_report_id = db.Column(db.Integer, db.ForeignKey("admin_report_submissions.id"), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    forwarded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    admin_note = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider = db.relationship("User", foreign_keys=[provider_id], backref="forwarded_patient_reports")
    admin_user = db.relationship("User", foreign_keys=[forwarded_by])


class DoctorReportRemark(db.Model):
    __tablename__ = "doctor_report_remarks"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"), nullable=False)
    remark = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    feedback_submitted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider = db.relationship("User", foreign_keys=[provider_id], backref="doctor_remarks_sent")
    patient = db.relationship("User", foreign_keys=[patient_id], backref="doctor_remarks_received")
    prediction = db.relationship("Prediction", backref="doctor_remarks")
