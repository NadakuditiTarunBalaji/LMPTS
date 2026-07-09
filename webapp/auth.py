from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g

from core.exceptions import AuthenticationError, ValidationError
from core.enums import UserRole
from core.notification import Notification

from webapp.auth_utils import services

auth_bp = Blueprint("auth", __name__)


def _dashboard_url_for(role: UserRole) -> str:
    return {
        UserRole.ADMIN: "admin.dashboard",
        UserRole.LEARNER: "learner.dashboard",
        UserRole.INSTRUCTOR: "instructor.dashboard",
        UserRole.ANALYST: "analyst.dashboard",
    }[role]


@auth_bp.route("/", methods=["GET"])
def index():
    if g.user is not None:
        return redirect(url_for(_dashboard_url_for(g.user.role)))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for(_dashboard_url_for(g.user.role)))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            user = services()["auth_service"].login(username, password)
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for(_dashboard_url_for(user.role)))
        except AuthenticationError as e:
            message = str(e)
            if message.startswith("PENDING:"):
                flash(message[len("PENDING:"):].strip(), "warning")
            elif message.startswith("REJECTED:"):
                flash(message[len("REJECTED:"):].strip(), "error")
            elif message.startswith("INACTIVE:"):
                flash(message[len("INACTIVE:"):].strip(), "error")
            else:
                flash("Invalid username or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for(_dashboard_url_for(g.user.role)))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html", form=request.form)

        try:
            user = services()["auth_service"].register_learner(
                username=username, password=password,
                full_name=full_name, email=email,
            )
            _notify_admins_of_registration(user)
            return render_template("auth/pending.html", username=user.username)
        except ValidationError as e:
            message = str(e)
            if "already taken" in message.lower():
                flash(f"Username '{username}' is already taken. Please choose a different username.", "error")
            else:
                flash(message, "error")
            return render_template("auth/register.html", form=request.form)

    return render_template("auth/register.html", form={})


def _notify_admins_of_registration(user) -> None:
    svc = services()
    notif_repo = svc.get("notification_repo")
    user_repo = svc.get("user_repo")
    if not notif_repo or not user_repo:
        return
    try:
        admins = user_repo.find_by_role(UserRole.ADMIN)
        for admin in admins:
            notif_repo.create(Notification(
                user_id=admin.id,
                message=(
                    f"New learner registration pending approval: "
                    f"'{user.username}' ({user.full_name}, {user.email}). "
                    f"Go to Pending Registrations to review."
                ),
            ))
    except Exception:
        pass
