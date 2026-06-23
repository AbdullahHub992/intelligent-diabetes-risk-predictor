import time
from collections import defaultdict

from flask import request

_login_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300


def is_login_rate_limited(username):
    key = f"{request.remote_addr}:{username}"
    now = time.time()
    _login_attempts[key] = [t for t in _login_attempts[key] if now - t < WINDOW_SECONDS]
    return len(_login_attempts[key]) >= MAX_ATTEMPTS


def record_failed_login(username):
    key = f"{request.remote_addr}:{username}"
    _login_attempts[key].append(time.time())


def clear_login_attempts(username):
    key = f"{request.remote_addr}:{username}"
    _login_attempts.pop(key, None)


def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
