from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session

from core.exceptions import ValidationError, AuthenticationError, LearnerNotFoundError
from core.enums import DifficultyLevel

from webapp.auth_utils import login_required, services

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/", methods=["GET"])
@login_required
def view():
    user = services()["profile_service"].get_profile(g.user.id)
    return render_template(
        "profile/view.html",
        user=user,
        difficulties=list(DifficultyLevel),
        tab=request.args.get("tab", "info"),
    )


@profile_bp.route("/personal-info", methods=["POST"])
@login_required
def update_personal_info():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    bio = request.form.get("bio", "").strip()
    preferred_difficulty = None
    if g.user.role.value == "LEARNER":
        raw = request.form.get("preferred_difficulty")
        if raw:
            preferred_difficulty = DifficultyLevel[raw]

    try:
        services()["profile_service"].update_personal_info(
            user_id=g.user.id, full_name=full_name, email=email,
            bio=bio, preferred_difficulty=preferred_difficulty,
        )
        flash("Profile updated.", "success")
    except (ValidationError, LearnerNotFoundError) as e:
        flash(str(e), "error")

    return redirect(url_for("profile.view", tab="info"))


@profile_bp.route("/password", methods=["POST"])
@login_required
def change_password():
    old_password = request.form.get("old_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if new_password != confirm_password:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("profile.view", tab="password"))

    try:
        services()["profile_service"].change_password(g.user.id, old_password, new_password)
        session.clear()
        flash("Password changed. Please log in again.", "success")
        return redirect(url_for("auth.login"))
    except (ValidationError, AuthenticationError, LearnerNotFoundError) as e:
        flash(str(e), "error")
        return redirect(url_for("profile.view", tab="password"))
