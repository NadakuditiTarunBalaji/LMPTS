"""
webapp
------
Flask web front-end for LMPTS, built on the same core/auth/algorithms/
repository/services layers used by the Tkinter GUI (see gui/app.py).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, render_template


def create_app(database=None):
    from gui.app import create_services, ensure_defaults_active, seed_sample_data
    from repository.database import Database

    app = Flask(__name__)
    app.secret_key = os.environ.get("LMPTS_SECRET_KEY", "dev-secret-key-change-in-production")

    if database is None:
        database = Database()
        database.initialize()

    services = create_services(database)
    services["auth_service"].create_default_users()
    ensure_defaults_active(services)
    seed_sample_data(services)

    app.config["SERVICES"] = services

    from webapp.auth import auth_bp
    from webapp.profile import profile_bp
    from webapp.admin import admin_bp
    from webapp.instructor import instructor_bp
    from webapp.learner import learner_bp
    from webapp.analyst import analyst_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(instructor_bp)
    app.register_blueprint(learner_bp)
    app.register_blueprint(analyst_bp)

    from webapp.auth_utils import register_request_hooks
    register_request_hooks(app)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    return app
