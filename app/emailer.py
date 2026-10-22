import json
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

from flask import current_app

from config import _load_dotenv


class MailNotConfigured(RuntimeError):
    """SMTP login is missing, so a verification email cannot be sent."""


def _mail_setting(name, default=""):
    _load_dotenv()
    value = os.environ.get(name) or current_app.config.get(name) or default
    value = str(value).strip().strip('"').strip("'")
    if name in ("MAIL_PASSWORD", "BREVO_API_KEY"):
        value = value.replace(" ", "")
    current_app.config[name] = value
    return value


def _send_via_brevo(to_email, subject, body, sender):
    """Send through Brevo's web API. Render's free plan blocks Gmail's SMTP ports."""
    api_key = _mail_setting("BREVO_API_KEY")
    payload = {
        "sender": {"name": "Intelligent Diabetes Risk Predictor", "email": sender},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }
    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        current_app.logger.error("Brevo rejected the email (%s): %s", exc.code, detail)
        raise


def _send_otp_email(to_email, subject, lines):
    username = str(_mail_setting("MAIL_USERNAME")).strip()
    password = str(_mail_setting("MAIL_PASSWORD"))
    sender = str(_mail_setting("MAIL_FROM") or username).strip()
    if not username or not password or not sender:
        raise MailNotConfigured("MAIL_USERNAME and MAIL_PASSWORD are required")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content("\n".join(lines))
    if _mail_setting("BREVO_API_KEY"):
        _send_via_brevo(to_email, subject, "\n".join(lines), sender)
        return

    with smtplib.SMTP(
        current_app.config.get("MAIL_SERVER", "smtp.gmail.com"),
        int(current_app.config.get("MAIL_PORT", 587)),
        timeout=20,
    ) as smtp:
        smtp.ehlo()
        if current_app.config.get("MAIL_USE_TLS", True):
            smtp.starttls()
            smtp.ehlo()
        smtp.login(username, password)
        smtp.send_message(message)


def send_registration_otp(to_email, code, role_label):
    minutes = current_app.config.get("OTP_EXPIRE_MINUTES", 10)
    _send_otp_email(
        to_email,
        "Your registration code — Intelligent Diabetes Risk Predictor",
        [
            f"Your verification code is {code}.",
            "",
            f"Use this code to finish {role_label} registration.",
            f"It expires in {minutes} minutes.",
            "",
            "If you did not try to register, you can ignore this email.",
        ],
    )


def send_password_reset_otp(to_email, code, role_label="account"):
    minutes = current_app.config.get("OTP_EXPIRE_MINUTES", 10)
    _send_otp_email(
        to_email,
        f"Your {role_label} password reset code — Intelligent Diabetes Risk Predictor",
        [
            f"Your {role_label} password reset code is {code}.",
            "",
            "This code changes only that account. Patient, healthcare provider, and admin passwords are separate.",
            "Enter this code on the matching login's Forgot password page, then choose a new password.",
            f"It expires in {minutes} minutes.",
            "",
            "If you did not ask to reset your password, you can ignore this email.",
        ],
    )
