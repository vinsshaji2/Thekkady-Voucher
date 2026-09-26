"""Single admin login (credentials from environment variables) + CSRF protection."""
import hmac
import os
import secrets
import time

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__)

PUBLIC_ENDPOINTS = {"auth.login", "static"}


def _credentials():
    """Returns (username, password, password_hash, using_local_default)."""
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
    local_default = False
    if not password and not password_hash and not current_app.config["ON_VERCEL"]:
        password, local_default = "admin", True
    return username, password, password_hash, local_default


def _check(username, password):
    exp_user, exp_pass, exp_hash, _ = _credentials()
    user_ok = hmac.compare_digest(username.encode(), exp_user.encode())
    if exp_hash:
        pass_ok = check_password_hash(exp_hash, password)
    elif exp_pass:
        pass_ok = hmac.compare_digest(password.encode(), exp_pass.encode())
    else:
        pass_ok = False
    return user_ok and pass_ok


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def _safe_next(target):
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("main.dashboard")


def init_auth(app):
    @app.before_request
    def _require_login():
        if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
            return None
        if not session.get("user"):
            nxt = request.full_path.rstrip("?") if request.method == "GET" else None
            return redirect(url_for("auth.login", next=nxt))
        return None

    @app.before_request
    def _check_csrf():
        if request.method == "POST":
            expected = session.get("csrf", "")
            sent = request.form.get("csrf_token", "")
            if not expected or not sent or not hmac.compare_digest(expected, sent):
                abort(400, description="Your session expired. Please go back, reload the page and try again.")

    app.jinja_env.globals["csrf_token"] = csrf_token


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("main.dashboard"))
    _, exp_pass, exp_hash, local_default = _credentials()
    not_configured = not exp_pass and not exp_hash
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if _check(username, password):
            session.clear()
            session.permanent = True
            session["user"] = username
            csrf_token()
            return redirect(_safe_next(request.args.get("next")))
        time.sleep(0.6)  # slow down guessing
        flash("Incorrect username or password.", "error")
    return render_template("login.html", local_default=local_default, not_configured=not_configured)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
