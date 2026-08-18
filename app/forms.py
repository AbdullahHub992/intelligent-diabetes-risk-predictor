from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import (
    BooleanField, FloatField, IntegerField, PasswordField,
    SelectField, StringField, SubmitField, TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, InputRequired, Length, NumberRange, Optional, URL


class LoginForm(FlaskForm):
    username = StringField("Username or Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


class ProfileSettingsForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])
    baseline_height_cm = FloatField("Baseline Height (cm)", validators=[Optional(), NumberRange(min=50, max=250)])
    baseline_weight_kg = FloatField("Baseline Weight (kg)", validators=[Optional(), NumberRange(min=20, max=300)])
    baseline_age = IntegerField("Baseline Age", validators=[Optional(), NumberRange(min=1, max=120)])
    baseline_sex = SelectField(
        "Baseline Sex",
        choices=[("", "Not set"), ("female", "Female"), ("male", "Male")],
        validators=[Optional()],
    )
    professional_credentials = StringField(
        "Professional Credentials",
        validators=[Optional(), Length(max=200)],
    )
    current_password = PasswordField(
        "Current Password",
        validators=[Optional(), Length(min=8)],
    )
    new_password = PasswordField(
        "New Password",
        validators=[Optional(), Length(min=8)],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[Optional(), EqualTo("new_password", message="Passwords must match")],
    )
    submit = SubmitField("Save Profile")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match")],
    )
    submit = SubmitField("Update Password")


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    role = SelectField(
        "Register As",
        choices=[
            ("patient", "Patient"),
            ("provider", "Healthcare Provider"),
        ],
        validators=[DataRequired()],
        default="patient",
    )
    professional_credentials = StringField(
        "Professional Credentials (for healthcare providers)",
        validators=[Optional(), Length(max=200)],
    )
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Register")


class ForgotPasswordLookupForm(FlaskForm):
    login = StringField("Username or Email", validators=[DataRequired()])
    submit = SubmitField("Continue")


class ForgotPasswordForm(FlaskForm):
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match")],
    )
    submit = SubmitField("Reset Password")


class ForgotPasswordEmailForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")


class AdminRegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Register Admin")


class CreateUserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    role = SelectField("Role", choices=[
        ("patient", "User (Patient)"),
        ("provider", "User (Healthcare Provider)"),
        ("admin", "Admin"),
    ])
    professional_credentials = StringField("Professional Credentials", validators=[Optional(), Length(max=200)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Create User")


class ExportReportForm(FlaskForm):
    prediction_id = SelectField(
        "Report Scope",
        coerce=int,
        validators=[InputRequired()],
    )
    report_format = SelectField(
        "Preferred Layout",
        choices=[("pdf", "PDF"), ("csv", "CSV")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Export Health Report")


class DatasetUploadForm(FlaskForm):
    dataset = FileField("Dataset CSV", validators=[Optional()])
    submit = SubmitField("Upload Dataset")
    use_sample = SubmitField("Load Built-in Sample Dataset")


class HealthDataForm(FlaskForm):
    sex = SelectField(
        "Sex",
        choices=[
            ("female", "Female"),
            ("male", "Male"),
        ],
        validators=[DataRequired()],
        default="female",
    )
    pregnancies = SelectField(
        "Pregnancies",
        choices=[
            (0, "0 — No / None"),
            (1, "1 — Yes (one pregnancy)"),
            (2, "2 — Two pregnancies"),
            (3, "3 pregnancies"),
            (4, "4 pregnancies"),
            (5, "5 pregnancies"),
            (6, "6 or more"),
        ],
        coerce=int,
        validators=[InputRequired()],
        default=0,
    )
    glucose = FloatField(
        "Glucose (Fasting Blood Sugar)",
        validators=[DataRequired(), NumberRange(min=0, max=300, message="Glucose must be between 0 and 300 mg/dL")],
        default=95,
    )
    systolic = FloatField(
        "Systolic Blood Pressure",
        validators=[DataRequired(), NumberRange(min=0, max=250, message="Systolic must be between 0 and 250")],
        default=120,
    )
    diastolic = FloatField(
        "Diastolic Blood Pressure",
        validators=[DataRequired(), NumberRange(min=0, max=150, message="Diastolic must be between 0 and 150")],
        default=80,
    )
    skin_thickness = FloatField(
        "Skin Thickness",
        validators=[DataRequired(), NumberRange(min=0, max=100, message="Skin thickness must be between 0 and 100")],
        default=20,
    )
    insulin = FloatField(
        "Insulin Level",
        validators=[DataRequired(), NumberRange(min=0, max=900, message="Insulin must be between 0 and 900")],
        default=80,
    )
    bmi = FloatField(
        "BMI",
        validators=[DataRequired(), NumberRange(min=10, max=70, message="BMI must be between 10 and 70")],
        default=25,
    )
    diabetes_pedigree = SelectField(
        "Family Diabetes History",
        choices=[
            (0, "0 — No (no diabetes in family)"),
            (1, "1 — Yes (diabetes in family)"),
        ],
        coerce=int,
        validators=[InputRequired()],
        default=0,
    )
    age = IntegerField(
        "Age",
        validators=[DataRequired(), NumberRange(min=1, max=120, message="Age must be between 1 and 120")],
        default=33,
    )
    smoking = SelectField(
        "Smoking Habit",
        choices=[
            ("never", "Never smoked"),
            ("former", "Former smoker"),
            ("current", "Current smoker"),
        ],
        validators=[DataRequired()],
        default="never",
    )
    physical_activity = SelectField(
        "Physical Activity",
        choices=[
            ("active", "Active (150+ min/week)"),
            ("moderate", "Moderate (some exercise)"),
            ("sedentary", "Sedentary (little exercise)"),
        ],
        validators=[DataRequired()],
        default="moderate",
    )
    diet_quality = SelectField(
        "Diet Quality",
        choices=[
            ("healthy", "Healthy (balanced diet)"),
            ("average", "Average"),
            ("poor", "Poor (high sugar/processed food)"),
        ],
        validators=[DataRequired()],
        default="average",
    )
    model_choice = SelectField("Prediction Model", choices=[], validators=[Optional()])
    submit = SubmitField("Generate Prediction")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if self.systolic.data is not None and self.diastolic.data is not None:
            if float(self.systolic.data) <= float(self.diastolic.data):
                self.systolic.errors.append(
                    "Systolic (top number) must be higher than diastolic (bottom number)."
                )
                return False
        return True


class FeedbackForm(FlaskForm):
    prediction_id = SelectField("Prediction to Review", coerce=int, validators=[DataRequired()])
    rating = SelectField(
        "Rating",
        choices=[("5", "Excellent"), ("4", "Good"), ("3", "Average"), ("2", "Poor"), ("1", "Very Poor")],
        validators=[DataRequired()],
    )
    actual_outcome = SelectField(
        "Actual Clinical Outcome",
        choices=[("", "Not specified"), ("0", "No Diabetes"), ("1", "Diabetes")],
        validators=[Optional()],
    )
    comment = TextAreaField("Comments", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Send Feedback to Admin")


class UserEditForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    role = SelectField("Role", choices=[
        ("patient", "User (Patient)"),
        ("provider", "User (Healthcare Provider)"),
        ("admin", "Admin"),
    ])
    professional_credentials = StringField("Professional Credentials", validators=[Optional(), Length(max=200)])
    is_active = BooleanField("Active Account")
    submit = SubmitField("Save Changes")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(), EqualTo("password", message="Passwords must match"),
    ])
    submit = SubmitField("Reset Password")


class EducationForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    category = SelectField("Category", choices=[
        ("risk_factors", "Risk Factors"),
        ("prevention", "Prevention"),
        ("lifestyle", "Lifestyle"),
        ("general", "General"),
    ])
    content = TextAreaField("Content", validators=[DataRequired()])
    external_url = StringField("External URL (optional)", validators=[Optional(), URL()])
    submit = SubmitField("Save Resource")


class ClinicalNoteForm(FlaskForm):
    note = TextAreaField("Clinical Note", validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField("Save Note")


class AssignDoctorPatientForm(FlaskForm):
    provider_id = SelectField("Healthcare Provider", coerce=int, validators=[DataRequired()])
    patient_id = SelectField("Patient", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Assign Patient to Provider")


class AssignPatientForm(FlaskForm):
    patient_id = SelectField("Patient", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Assign Patient")


class ModelSelectForm(FlaskForm):
    production_model = SelectField("Production Model", choices=[], validators=[DataRequired()])
    submit = SubmitField("Set Production Model")
