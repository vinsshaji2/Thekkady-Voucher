"""Thekkady Adventures booking desk — Flask app factory."""
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask

from .extensions import db

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)


def _database_url():
    url = (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or "").strip()
    if not url:
        # Neon's Vercel integration may add a custom prefix, e.g. STORAGE_DATABASE_URL
        for key in sorted(os.environ):
            if key.endswith(("_DATABASE_URL", "_POSTGRES_URL")) and "UNPOOLED" not in key:
                url = os.environ[key].strip()
                break
    if not url:
        if os.environ.get("VERCEL"):
            raise RuntimeError(
                "DATABASE_URL is not set. Connect a Neon database in Vercel -> Storage, then redeploy."
            )
        # Local development: a SQLite file inside ./instance
        os.makedirs(os.path.join(PROJECT_DIR, "instance"), exist_ok=True)
        path = os.path.join(PROJECT_DIR, "instance", "bookings.db").replace("\\", "/")
        return "sqlite:///" + path
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def create_app():
    load_dotenv(os.path.join(PROJECT_DIR, ".env"))
    on_vercel = bool(os.environ.get("VERCEL"))

    secret = os.environ.get("SECRET_KEY")
    if not secret:
        if on_vercel:
            raise RuntimeError("SECRET_KEY is not set in the Vercel environment variables.")
        secret = "local-dev-only-secret"

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secret,
        SQLALCHEMY_DATABASE_URI=_database_url(),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 280},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=on_vercel,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        SEND_FILE_MAX_AGE_DEFAULT=timedelta(days=7),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        ON_VERCEL=on_vercel,
    )

    db.init_app(app)

    from . import models  # noqa: F401  (register tables)
    from .auth import bp as auth_bp, init_auth
    from .routes import bp as main_bp
    from .filters import register_filters

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    init_auth(app)
    register_filters(app)

    with app.app_context():
        db.create_all()

    return app
