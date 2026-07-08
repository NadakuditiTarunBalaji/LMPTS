"""
webapp.auth_utils
-----------------
Per-request identity for the Flask app.

Identity is tracked with Flask's own signed-cookie session (session['user_id']),
NOT auth.session_manager.SessionManager -- that class is a process-wide
singleton holding a single "current user" slot, which is correct for the
single-user Tkinter app but would let concurrent web users overwrite each
other's login state. AuthService.login()/register_learner() are still used
for credential verification and business rules (they raise the same
AuthenticationError/ValidationError as the desktop app).
"""

from functools import wraps

from flask import session, g, redirect, url_for, flash, abort, current_app


def services():
    return current_app.config["SERVICES"]


def register_request_hooks(app):
    @app.before_request
    def load_current_user():
        g.user = None
        user_id = session.get("user_id")
        if user_id is not None:
            g.user = services()["user_repo"].get_user(user_id)
            if g.user is None:
                session.clear()

    @app.context_processor
    def inject_user():
        return {"current_user": g.get("user")}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                flash("Please log in to continue.", "error")
                return redirect(url_for("auth.login"))
            if g.user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def current_learner_id():
    """Resolve the Learner.id linked to the logged-in user, or None."""
    learner = services()["learner_repo"].get_learner_by_user_id(g.user.id)
    return learner.id if learner else None
