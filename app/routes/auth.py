from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.decorators import role_required
from app.forms import LoginForm, ProfileSettingsForm, RegisterForm, StaffLoginForm
from app.models import User
from app.security import clear_login_attempts, is_login_rate_limited, record_failed_login
from app.utils import log_audit, redirect_to_role_home, verify_owner_access_code

auth_bp = Blueprint("auth", __name__)

LOGIN_PORTALS = {
    "patient": {
        "role": "patient",
        "title": "Patient Login",
        "subtitle": "Access your health records, predictions, and progress.",
        "icon": "patient",
        "demo": "patient / patient123",
        "requires_owner_code": False,
    },
    "doctor": {
        "role": "provider",
        "title": "Doctor Login",
        "subtitle": "Restricted access. Use credentials and owner access code provided by the system owner.",
        "icon": "doctor",
        "demo": None,
        "requires_owner_code": True,
    },
    "admin": {
        "role": "admin",
        "title": "Admin Login",
        "subtitle": "Restricted access. Use credentials and owner access code provided by the system owner.",
        "icon": "admin",
        "demo": None,
        "requires_owner_code": True,
    },
}

ROLE_LABELS = {
    "patient": "Patient",
    "provider": "Doctor",
    "admin": "Administrator",
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

    form = StaffLoginForm() if portal["requires_owner_code"] else LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        if is_login_rate_limited(username):
            flash("Too many failed attempts. Please try again in 5 minutes.", "danger")
            return render_template("login.html", form=form, portal=portal, portal_key=portal_key)

        if portal["requires_owner_code"]:
            if not verify_owner_access_code(portal_key, form.owner_access_code.data):
                record_failed_login(username)
                other_portal = "admin" if portal_key == "doctor" else "doctor"
                if verify_owner_access_code(other_portal, form.owner_access_code.data):
                    flash(
                        f"You entered the {other_portal} access code. "
                        f"Use the {portal_key} access code on this page.",
                        "danger",
                    )
                else:
                    flash("Invalid owner access code. Contact the system owner for access.", "danger")
                return render_template("login.html", form=form, portal=portal, portal_key=portal_key)

        user = _find_user_by_login(username)
        if user and user.is_active and user.check_password(form.password.data):
            if user.role != portal["role"]:
                record_failed_login(username)
                flash(
                    f"This account is registered as {ROLE_LABELS.get(user.role, user.role)}. "
                    f"Please use the {ROLE_LABELS.get(user.role, user.role)} login button on the home page.",
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


@auth_bp.route("/login/patient", methods=["GET", "POST"])
def login_patient():
    return _handle_login("patient")


@auth_bp.route("/login/doctor", methods=["GET", "POST"])
def login_doctor():
    return _handle_login("doctor")


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
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                full_name=form.full_name.data,
                role="patient",
                is_active=True,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            log_audit("register", "user", f"username={user.username}")
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("admin", "provider")
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

        current_user.full_name = form.full_name.data
        current_user.username = form.username.data
        current_user.email = form.email.data
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
        db.session.commit()
        log_audit("update_profile", "user", f"username={current_user.username}")
        flash("Your profile has been updated successfully.", "success")
        return redirect(url_for("auth.profile_settings"))

    return render_template("profile_settings.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_audit("logout", "user")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
