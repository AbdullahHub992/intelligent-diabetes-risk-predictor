import os
import smtplib
from email.message import EmailMessage

from flask import current_app

from config import _load_dotenv


class MailNotConfigured(RuntimeError):
    """SMTP login is missing, so a verification email cannot be sent."""


def _mail_setting(name, default=""):
    _load_dotenv()
    value = os.environ.get(name) or current_app.config.get(name) or default
    if name == "MAIL_PASSWORD":
        value = str(value).replace(" ", "")
    current_app.config[name] = value
    return value


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


def send_password_reset_otp(to_email, code):
    minutes = current_app.config.get("OTP_EXPIRE_MINUTES", 10)
    _send_otp_email(
        to_email,
        "Your password reset code — Intelligent Diabetes Risk Predictor",
        [
            f"Your password reset code is {code}.",
            "",
            "Enter this code on the website, then choose a new password.",
            f"It expires in {minutes} minutes.",
            "",
            "If you did not ask to reset your password, you can ignore this email.",
        ],
    )
