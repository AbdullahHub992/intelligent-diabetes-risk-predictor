from flask import Blueprint, abort, flash, redirect, render_template, session, url_for
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.forms import (
    AdminRegisterForm, ChangePasswordForm,
    ForgotPasswordForm, ForgotPasswordLookupForm, LoginForm, ProfileSettingsForm,
    RegisterForm, ResetPasswordForm,
)
from app.models import PasswordResetToken, User
from app.security import clear_login_attempts, is_login_rate_limited, record_failed_login
from app.utils import log_audit, redirect_to_role_home

auth_bp = Blueprint("auth", __name__)

LOGIN_PORTALS = {
    "user": {
        "roles": ["patient", "provider"],
        "title": "User Login",
        "subtitle": "Patients and healthcare providers — predictions, dashboards, reports, education, and clinical support.",
        "icon": "user",
        "demo": "patient / patient123  ·  doctor / doctor123",
    },
    "admin": {
        "roles": ["admin"],
        "title": "Admin Login",
        "subtitle": "System administrator — dataset import, model training, and account management.",
        "icon": "admin",
        "demo": "admin / admin123",
    },
}

ROLE_LABELS = {
    "patient": "User (Patient)",
    "provider": "User (Healthcare Provider)",
    "admin": "Administrator",
}

PORTAL_LABELS = {
    "user": "User",
    "admin": "Admin",
}


def _find_user_by_login(login_value):
    from sqlalchemy import func

    login_value = login_value.strip()
    if not login_value:
        return None
    user = User.query.filter_by(username=login_value).first()
    if user:
        return user
    if "@" in login_value:
        return User.query.filter(func.lower(User.email) == login_value.lower()).first()
    return None


def _handle_login(portal_key):
    if current_user.is_authenticated:
        return redirect_to_role_home()

    portal = LOGIN_PORTALS.get(portal_key)
    if not portal:
        abort(404)

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        if is_login_rate_limited(username):
            flash("Too many failed attempts. Please try again in 5 minutes.", "danger")
            return render_template("login.html", form=form, portal=portal, portal_key=portal_key)

        user = _find_user_by_login(username)
        allowed_roles = portal["roles"]
        if user and user.is_active and user.check_password(form.password.data):
            if user.role not in allowed_roles:
                record_failed_login(username)
                target = "Admin Login" if user.is_admin else "User Login"
                flash(
                    f"This account belongs to the {ROLE_LABELS.get(user.role, user.role)} panel. "
                    f"Please use {target} on the home page.",
                    "danger",
                )
                return render_template("login.html", form=form, portal=portal, portal_key=portal_key)

            login_user(user, remember=form.remember.data)
            clear_login_attempts(username)
            log_audit("login", "user", f"username={username}, portal={portal_key}")
            flash("Logged in successfully. You can update your profile from the menu.", "success")
            return redirect_to_role_home()

        record_failed_login(username)
        flash(
            "Invalid username/email or password. Use your registered username or email — not your full name.",
            "danger",
        )

    return render_template("login.html", form=form, portal=portal, portal_key=portal_key)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect_to_role_home()
    return redirect(url_for("main.index") + "#login")


@auth_bp.route("/login/user", methods=["GET", "POST"])
def user_login():
    return _handle_login("user")


@auth_bp.route("/login/patient", methods=["GET", "POST"])
def login_patient():
    return redirect(url_for("auth.user_login"))


@auth_bp.route("/login/doctor", methods=["GET", "POST"])
def login_doctor():
    return redirect(url_for("auth.user_login"))


@auth_bp.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    return _handle_login("admin")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect_to_role_home()
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already exists.", "danger")
        elif User.query.filter_by(email=form.email.data).first():
            flash("Email already registered.", "danger")
        elif form.role.data == "provider" and not (form.professional_credentials.data or "").strip():
            flash("Healthcare providers must provide professional credentials (e.g. license or hospital ID).", "danger")
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                full_name=form.full_name.data,
                role=form.role.data,
                professional_credentials=(form.professional_credentials.data or "").strip() or None,
                is_active=True,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            log_audit("register", "user", f"username={user.username}, role={user.role}")
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.user_login"))
    return render_template("register.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect_to_role_home()

    lookup_form = ForgotPasswordLookupForm()
    reset_form = ForgotPasswordForm()
    user_id = session.get("recovery_user_id")
    user = User.query.get(user_id) if user_id else None

    if user and reset_form.validate_on_submit():
        user.set_password(reset_form.new_password.data)
        session.pop("recovery_user_id", None)
        db.session.commit()
        log_audit("password_recovery", "user", f"username={user.username}")
        flash("Password reset successful. Please log in.", "success")
        return _redirect_login_for_role(user.role)

    if lookup_form.validate_on_submit():
        user = _find_user_by_login(lookup_form.login.data)
        if not user:
            flash("No account found with that username or email.", "danger")
            return render_template(
                "forgot_password.html", lookup_form=lookup_form, reset_form=reset_form,
            )
        session["recovery_user_id"] = user.id
        return redirect(url_for("auth.forgot_password"))

    return render_template(
        "forgot_password.html",
        user=user,
        lookup_form=lookup_form,
        reset_form=reset_form,
    )


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_email(token):
    from datetime import datetime
    from werkzeug.security import check_password_hash

    if current_user.is_authenticated:
        return redirect_to_role_home()

    record = PasswordResetToken.query.order_by(PasswordResetToken.created_at.desc()).all()
    matched = None
    for row in record:
        if check_password_hash(row.token_hash, token) and row.expires_at > datetime.utcnow():
            matched = row
            break
    if not matched:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("auth.forgot_password", method="email"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.get(matched.user_id)
        user.set_password(form.password.data)
        PasswordResetToken.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        log_audit("password_recovery", "user", f"username={user.username}, method=email")
        flash("Password reset successful. Please log in.", "success")
        return _redirect_login_for_role(user.role)

    return render_template("reset_password_email.html", form=form)


def _redirect_login_for_role(role):
    if role == "admin":
        return redirect(url_for("auth.login_admin"))
    return redirect(url_for("auth.user_login"))


@auth_bp.route("/register/admin", methods=["GET", "POST"])
def register_admin():
    """UC_08: Admin registration."""
    if current_user.is_authenticated:
        return redirect_to_role_home()
    form = AdminRegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already exists.", "danger")
        elif User.query.filter_by(email=form.email.data).first():
            flash("Email already registered.", "danger")
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                full_name=form.full_name.data,
                role="admin",
                is_active=True,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            log_audit("register", "user", f"username={user.username}, role=admin")
            flash("Admin registration successful. Please log in.", "success")
            return redirect(url_for("auth.login_admin"))
    return render_template("admin_register.html", form=form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """UC_06: Change Password."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            log_audit("change_password", "user", f"username={current_user.username}")
            flash("Password updated successfully.", "success")
            return redirect(url_for("auth.profile_settings"))
    return render_template("change_password.html", form=form)


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile_settings():
    form = ProfileSettingsForm(obj=current_user)
    if form.validate_on_submit():
        existing_user = User.query.filter(
            User.username == form.username.data,
            User.id != current_user.id,
        ).first()
        if existing_user:
            flash("Username already taken. Choose another.", "danger")
            return render_template("profile_settings.html", form=form)

        existing_email = User.query.filter(
            User.email == form.email.data,
            User.id != current_user.id,
        ).first()
        if existing_email:
            flash("Email already in use. Choose another.", "danger")
            return render_template("profile_settings.html", form=form)

        if form.new_password.data:
            if not form.current_password.data:
                flash("Enter your current password to set a new password.", "danger")
                return render_template("profile_settings.html", form=form)
            if not current_user.check_password(form.current_password.data):
                flash("Current password is incorrect.", "danger")
                return render_template("profile_settings.html", form=form)
            current_user.set_password(form.new_password.data)

        current_user.full_name = form.full_name.data
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.phone = (form.phone.data or "").strip() or None
        current_user.address = (form.address.data or "").strip() or None
        current_user.baseline_height_cm = form.baseline_height_cm.data
        current_user.baseline_weight_kg = form.baseline_weight_kg.data
        current_user.baseline_age = form.baseline_age.data
        current_user.baseline_sex = form.baseline_sex.data or None
        if current_user.is_provider:
            current_user.professional_credentials = (form.professional_credentials.data or "").strip() or None
        db.session.commit()
        log_audit("update_profile", "user", f"username={current_user.username}")
        flash("Your profile has been updated successfully.", "success")
        return redirect(url_for("auth.profile_settings"))

    return render_template("profile_settings.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    role = current_user.role
    log_audit("logout", "user")
    logout_user()
    flash("You have been logged out securely.", "info")
    return _redirect_login_for_role(role)
