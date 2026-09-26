import os

from . import calc


def fmt_date(value, pattern="%d %b %Y"):
    return value.strftime(pattern) if value else ""


def register_filters(app):
    app.jinja_env.filters["inr"] = calc.inr
    app.jinja_env.filters["date"] = fmt_date

    def asset(filename):
        """Static URL with a file-modified stamp, so browsers pick up new CSS/JS after each deploy."""
        from flask import url_for

        version = os.environ.get("VERCEL_DEPLOYMENT_ID") or os.environ.get("VERCEL_GIT_COMMIT_SHA", "")[:12]
        if not version:
            path = os.path.join(app.static_folder, filename)
            version = int(os.path.getmtime(path)) if os.path.exists(path) else 0
        return url_for("static", filename=filename, v=version)

    app.jinja_env.globals["asset"] = asset

    @app.context_processor
    def _inject():
        from flask import session
        from .settings import get_settings

        # The login page renders before a session exists; settings are harmless there.
        return {"S": get_settings(), "is_logged_in": bool(session.get("user"))}
