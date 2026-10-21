import secrets
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.emailer import MailNotConfigured, send_password_reset_otp, send_registration_otp
from app.forms import (
    AdminLoginForm, AdminRegisterForm, ChangePasswordForm,
    ForgotPasswordForm, ForgotPasswordLookupForm, LoginForm, ProfileSettingsForm,
    RegisterForm, RegistrationOtpForm, ResetPasswordForm,
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
        "demo": None,
    },
    "admin": {
        "roles": ["admin"],
        "title": "Admin Login",
        "subtitle": "System administrator — dataset import, model training, and account management.",
        "icon": "admin",
        "demo": None,
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


def _normalize_username(value):
    return (value or "").strip()


def _normalize_email(value):
    return (value or "").strip().lower()


def _find_user_by_login(login_value):
    from sqlalchemy import func

    login_value = (login_value or "").strip()
    if not login_value:
        return None
    user = User.query.filter(func.lower(User.username) == login_value.lower()).first()
    if user:
        return user
    return User.query.filter(func.lower(User.email) == login_value.lower()).first()


def _email_taken(email, ignore_user_id=None):
    from sqlalchemy import func

    query = User.query.filter(func.lower(User.email) == _normalize_email(email))
    if ignore_user_id:
        query = query.filter(User.id != ignore_user_id)
    return query.first()


def _username_taken(username, ignore_user_id=None):
    from sqlalchemy import func

    query = User.query.filter(func.lower(User.username) == _normalize_username(username).lower())
    if ignore_user_id:
        query = query.filter(User.id != ignore_user_id)
    return query.first()


def _handle_login(portal_key):
    if current_user.is_authenticated:
        return redirect_to_role_home()

    portal = LOGIN_PORTALS.get(portal_key)
    if not portal:
        abort(404)

    form = AdminLoginForm() if portal_key == "admin" else LoginForm()
    if form.validate_on_submit():
        username = _normalize_username(form.username.data)
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

            if portal_key == "admin" and not _admin_access_code_ok(form.access_code.data):
                record_failed_login(username)
                flash("That access code is not valid. Enter one of the three admin access codes.", "danger")
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


ROLE_EMAIL_LABELS = {
    "patient": "patient",
    "provider": "healthcare provider",
    "admin": "administrator",
}


def _mask_email(email):
    local, _, domain = (email or "").partition("@")
    if not local or not domain:
        return email
    visible = local[:1]
    return f"{visible}{'*' * max(len(local) - 1, 1)}@{domain}"


def _issue_registration_otp(pending):
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.utcnow()
    pending["otp_hash"] = generate_password_hash(code)
    pending["expires_at"] = (now + timedelta(minutes=current_app.config.get("OTP_EXPIRE_MINUTES", 10))).isoformat()
    pending["last_sent"] = now.isoformat()
    pending["attempts"] = 0
    session["pending_registration"] = pending
    session.modified = True
    try:
        send_registration_otp(pending["email"], code, ROLE_EMAIL_LABELS.get(pending["role"], "account"))
    except Exception:
        session.pop("pending_registration", None)
        raise
    return code


def _registration_blocked(username, email, role, credentials):
    if _username_taken(username):
        flash("Username already exists.", "danger")
        return True
    if _email_taken(email):
        flash("Email already registered.", "danger")
        return True
    if role == "provider" and not (credentials or "").strip():
        flash("Healthcare providers must provide professional credentials (e.g. license or hospital ID).", "danger")
        return True
    return False


def _otp_send_failed(exc):
    if isinstance(exc, MailNotConfigured):
        flash(
            "Email verification is not set up yet. Add the sender mailbox in MAIL_USERNAME and MAIL_PASSWORD, then register again.",
            "danger",
        )
        return
    current_app.logger.exception("registration otp email failed")
    flash("We could not send the verification email. Check the address and try again.", "danger")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect_to_role_home()
    form = RegisterForm()
    if form.validate_on_submit():
        username = _normalize_username(form.username.data)
        email = _normalize_email(form.email.data)
        credentials = (form.professional_credentials.data or "").strip() or None
        if not _registration_blocked(username, email, form.role.data, credentials):
            try:
                _issue_registration_otp({
                    "username": username,
                    "email": email,
                    "full_name": form.full_name.data.strip(),
                    "role": form.role.data,
                    "professional_credentials": credentials,
                    "password_hash": generate_password_hash(form.password.data),
                    "cancel_endpoint": "auth.register",
                })
            except Exception as exc:
                _otp_send_failed(exc)
            else:
                flash(f"We sent a 6-digit code to {email}.", "info")
                return redirect(url_for("auth.verify_registration"))
    return render_template("register.html", form=form)


@auth_bp.route("/register/verify", methods=["GET", "POST"])
def verify_registration():
    if current_user.is_authenticated:
        return redirect_to_role_home()

    pending = session.get("pending_registration")
    if not pending:
        flash("Start registration again so we can email you a new code.", "info")
        return redirect(url_for("auth.register"))

    expires_at = datetime.fromisoformat(pending["expires_at"])
    if expires_at <= datetime.utcnow():
        session.pop("pending_registration", None)
        flash("That code expired. Register again to get a new one.", "danger")
        return redirect(url_for(pending.get("cancel_endpoint") or "auth.register"))

    form = RegistrationOtpForm()
    if request_is_resend():
        last_sent = datetime.fromisoformat(pending["last_sent"])
        if (datetime.utcnow() - last_sent).total_seconds() < 60:
            flash("Wait a minute before requesting another code.", "warning")
        else:
            try:
                _issue_registration_otp(pending)
            except Exception as exc:
                _otp_send_failed(exc)
            else:
                flash(f"A new code was sent to {pending['email']}.", "info")
        return redirect(url_for("auth.verify_registration"))

    if form.validate_on_submit():
        if not check_password_hash(pending["otp_hash"], (form.otp.data or "").strip()):
            pending["attempts"] = int(pending.get("attempts") or 0) + 1
            if pending["attempts"] >= 5:
                session.pop("pending_registration", None)
                flash("Too many incorrect codes. Register again to get a new one.", "danger")
                return redirect(url_for(pending.get("cancel_endpoint") or "auth.register"))
            session["pending_registration"] = pending
            session.modified = True
            flash("That code is incorrect.", "danger")
        elif _registration_blocked(
            pending["username"], pending["email"], pending["role"], pending.get("professional_credentials")
        ):
            session.pop("pending_registration", None)
            return redirect(url_for(pending.get("cancel_endpoint") or "auth.register"))
        else:
            user = User(
                username=pending["username"],
                email=pending["email"],
                full_name=pending["full_name"],
                role=pending["role"],
                professional_credentials=pending.get("professional_credentials"),
                password_hash=pending["password_hash"],
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()
            session.pop("pending_registration", None)
            log_audit("register", "user", f"username={user.username}, role={user.role}, email_verified=true")
            login_user(user)
            flash(
                f"Email verified. You are signed in as {user.username}.",
                "success",
            )
            return redirect_to_role_home()

    return render_template(
        "verify_otp.html",
        form=form,
        masked_email=_mask_email(pending["email"]),
        role_label=ROLE_EMAIL_LABELS.get(pending["role"], "account"),
        cancel_endpoint=pending.get("cancel_endpoint") or "auth.register",
    )


def _admin_access_code_ok(value):
    entered = (value or "").strip().casefold()
    allowed = current_app.config.get("ADMIN_ACCESS_CODES") or ()
    return bool(entered) and entered in {str(code).strip().casefold() for code in allowed}


def request_is_resend():
    return request.method == "POST" and request.form.get("resend") == "1"


def _pending_password_reset():
    pending = session.get("pending_password_reset")
    if not pending:
        return None
    if datetime.fromisoformat(pending["expires_at"]) <= datetime.utcnow():
        session.pop("pending_password_reset", None)
        return None
    return pending


def _issue_password_reset_otp(user):
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.utcnow()
    pending = {
        "user_id": user.id,
        "email": user.email,
        "otp_hash": generate_password_hash(code),
        "expires_at": (now + timedelta(minutes=current_app.config.get("OTP_EXPIRE_MINUTES", 10))).isoformat(),
        "last_sent": now.isoformat(),
        "attempts": 0,
        "verified": False,
    }
    session["pending_password_reset"] = pending
    session.modified = True
    try:
        send_password_reset_otp(user.email, code)
    except Exception:
        session.pop("pending_password_reset", None)
        raise
    return code


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect_to_role_home()

    lookup_form = ForgotPasswordLookupForm()
    otp_form = RegistrationOtpForm()
    reset_form = ForgotPasswordForm()
    pending = _pending_password_reset()

    if request.method == "POST" and pending and request_is_resend() and not pending.get("verified"):
        last_sent = datetime.fromisoformat(pending["last_sent"])
        if (datetime.utcnow() - last_sent).total_seconds() < 60:
            flash("Wait a minute before requesting another code.", "warning")
        else:
            user = db.session.get(User, pending["user_id"])
            if not user or not user.is_active:
                session.pop("pending_password_reset", None)
                flash("Start password recovery again.", "danger")
                return redirect(url_for("auth.forgot_password"))
            try:
                _issue_password_reset_otp(user)
            except Exception as exc:
                _otp_send_failed(exc)
            else:
                flash(f"A new code was sent to {_mask_email(user.email)}.", "info")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST" and pending and not pending.get("verified") and request.form.get("otp") is not None:
        if otp_form.validate_on_submit():
            if not check_password_hash(pending["otp_hash"], (otp_form.otp.data or "").strip()):
                pending["attempts"] = int(pending.get("attempts") or 0) + 1
                if pending["attempts"] >= 5:
                    session.pop("pending_password_reset", None)
                    flash("Too many incorrect codes. Start password recovery again.", "danger")
                    return redirect(url_for("auth.forgot_password"))
                session["pending_password_reset"] = pending
                session.modified = True
                flash("That code is incorrect.", "danger")
            else:
                pending["verified"] = True
                session["pending_password_reset"] = pending
                session.modified = True
                flash("Code verified. Choose a new password.", "success")
        return render_template(
            "forgot_password.html",
            lookup_form=lookup_form,
            otp_form=otp_form,
            reset_form=reset_form,
            pending=session.get("pending_password_reset"),
            masked_email=_mask_email(pending["email"]),
        )

    if request.method == "POST" and pending and pending.get("verified") and request.form.get("new_password") is not None:
        if reset_form.validate_on_submit():
            user = db.session.get(User, pending["user_id"])
            if not user or not user.is_active:
                session.pop("pending_password_reset", None)
                flash("That account is no longer available. Register again.", "danger")
                return redirect(url_for("auth.register"))
            user.set_password(reset_form.new_password.data)
            session.pop("pending_password_reset", None)
            db.session.commit()
            log_audit("password_recovery", "user", f"username={user.username}, method=email_otp")
            flash("Password reset successful. Please log in.", "success")
            return _redirect_login_for_role(user.role)
        return render_template(
            "forgot_password.html",
            lookup_form=lookup_form,
            otp_form=otp_form,
            reset_form=reset_form,
            pending=pending,
            masked_email=_mask_email(pending["email"]),
        )

    if lookup_form.validate_on_submit():
        user = _find_user_by_login(lookup_form.login.data)
        if not user or not user.is_active:
            flash(
                "No account found with that username or email. Register again if you do not have an account.",
                "danger",
            )
        else:
            try:
                _issue_password_reset_otp(user)
            except Exception as exc:
                _otp_send_failed(exc)
            else:
                flash(f"We sent a 6-digit code to {_mask_email(user.email)}.", "info")
                return redirect(url_for("auth.forgot_password"))

    pending = _pending_password_reset()
    return render_template(
        "forgot_password.html",
        lookup_form=lookup_form,
        otp_form=otp_form,
        reset_form=reset_form,
        pending=pending,
        masked_email=_mask_email(pending["email"]) if pending else "",
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
        username = _normalize_username(form.username.data)
        email = _normalize_email(form.email.data)
        if not _registration_blocked(username, email, "admin", None):
            try:
                _issue_registration_otp({
                    "username": username,
                    "email": email,
                    "full_name": form.full_name.data.strip(),
                    "role": "admin",
                    "professional_credentials": None,
                    "password_hash": generate_password_hash(form.password.data),
                    "cancel_endpoint": "auth.register_admin",
                })
            except Exception as exc:
                _otp_send_failed(exc)
            else:
                flash(f"We sent a 6-digit code to {email}.", "info")
                return redirect(url_for("auth.verify_registration"))
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
