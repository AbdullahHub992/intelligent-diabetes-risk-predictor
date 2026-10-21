import json

from app import create_app
from app.emailer import send_registration_otp


def test_registration_email_uses_brevo_when_api_key_is_set(monkeypatch):
    captured = {}

    class FakeResponse:
        def read(self):
            return b'{"messageId":"1"}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout=20):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode())
        captured["key"] = request.get_header("Api-key")
        return FakeResponse()

    def smtp_must_not_run(*args, **kwargs):
        raise AssertionError("SMTP should not be used when Brevo is configured")

    monkeypatch.setenv("BREVO_API_KEY", "test-key")
    monkeypatch.setenv("MAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "app-password")
    monkeypatch.setenv("MAIL_FROM", "sender@example.com")
    monkeypatch.setattr("app.emailer.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("app.emailer.smtplib.SMTP", smtp_must_not_run)

    app = create_app()
    with app.app_context():
        send_registration_otp("person@example.com", "123456", "patient")

    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["key"] == "test-key"
    assert captured["body"]["sender"]["email"] == "sender@example.com"
    assert captured["body"]["to"] == [{"email": "person@example.com"}]
    assert "123456" in captured["body"]["textContent"]
