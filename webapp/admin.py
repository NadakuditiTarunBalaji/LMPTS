import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from core.enums import UserRole, DifficultyLevel, CourseStatus
from core.exceptions import (
    ValidationError, CourseNotFoundError, CircularDependencyError,
    LearnerNotFoundError,
)
from core.course import Course
from core.learner import Learner
from core.notification import Notification
from auth.password_manager import PasswordManager

from webapp.auth_utils import services, role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@role_required(UserRole.ADMIN)
def _guard():
    pass


@admin_bp.route("/")
def dashboard():
    svc = services()
    overview = svc["analytics_service"].system_overview()
    activity = svc["analytics_service"].learner_activity_report()
    pending_count = svc["account_service"].count_pending()
    return render_template("admin/dashboard.html", overview=overview, activity=activity[:10], pending_count=pending_count)


# ── Pending registrations ────────────────────────────────────────────────────

@admin_bp.route("/registrations")
def registrations():
    svc = services()
    pending = svc["account_service"].get_pending_registrations()
    all_users = svc["account_service"].get_all_users_with_status()
    return render_template("admin/registrations.html", pending=pending, all_users=all_users,
                            tab=request.args.get("tab", "pending"))


@admin_bp.route("/registrations/<int:user_id>/approve", methods=["POST"])
def approve_registration(user_id):
    note = request.form.get("note", "")
    try:
        services()["account_service"].approve_registration(user_id, admin_id=_admin_id(), note=note)
        flash("Registration approved.", "success")
    except (ValidationError, LearnerNotFoundError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.registrations"))


@admin_bp.route("/registrations/<int:user_id>/reject", methods=["POST"])
def reject_registration(user_id):
    reason = request.form.get("reason", "").strip()
    try:
        services()["account_service"].reject_registration(user_id, admin_id=_admin_id(), rejection_reason=reason)
        flash("Registration rejected.", "success")
    except (ValidationError, LearnerNotFoundError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.registrations"))


@admin_bp.route("/registrations/<int:user_id>/request-info", methods=["POST"])
def request_more_information(user_id):
    message = request.form.get("message", "").strip()
    try:
        services()["account_service"].request_more_information(user_id, admin_id=_admin_id(), message=message)
        flash("Requested more information from the applicant.", "success")
    except (ValidationError, LearnerNotFoundError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.registrations"))


@admin_bp.route("/registrations/<int:user_id>/deactivate", methods=["POST"])
def deactivate_user(user_id):
    try:
        services()["account_service"].deactivate_user(user_id, admin_id=_admin_id())
        flash("User deactivated.", "success")
    except LearnerNotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.registrations", tab="all"))


@admin_bp.route("/registrations/<int:user_id>/reactivate", methods=["POST"])
def reactivate_user(user_id):
    try:
        services()["account_service"].reactivate_user(user_id, admin_id=_admin_id())
        flash("User reactivated.", "success")
    except LearnerNotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.registrations", tab="all"))


# ── Users ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/users")
def users():
    all_users = services()["user_repo"].get_all_users()
    return render_template("admin/users.html", users=all_users, roles=list(UserRole))


@admin_bp.route("/users/create", methods=["POST"])
def create_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = UserRole[request.form.get("role", "LEARNER")]
    try:
        services()["auth_service"].register(username, password, role)
        flash(f"User '{username}' created.", "success")
    except ValidationError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    services()["user_repo"].delete_user(user_id)
    flash("User deleted.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/change-password", methods=["POST"])
def admin_change_password(user_id):
    new_password = request.form.get("new_password", "")
    try:
        user = services()["user_repo"].get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        password_hash = PasswordManager.hash_password(new_password)
        services()["user_repo"].update_password(user_id, password_hash)
        flash(f"Password reset for '{user.username}'.", "success")
    except (ValidationError, LearnerNotFoundError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.users"))


def _admin_id():
    from flask import g
    return g.user.id


# ── Courses ───────────────────────────────────────────────────────────────────

@admin_bp.route("/courses")
def courses():
    course_service = services()["course_service"]
    all_courses = course_service.get_all_courses()
    return render_template("admin/courses.html", courses=all_courses,
                            difficulties=list(DifficultyLevel))


@admin_bp.route("/courses/create", methods=["POST"])
def create_course():
    try:
        course = Course(
            code=request.form.get("code", "").strip().upper(),
            name=request.form.get("name", "").strip(),
            difficulty=DifficultyLevel[request.form.get("difficulty", "BEGINNER")],
            duration=int(request.form.get("duration", 0) or 0),
            description=request.form.get("description", "").strip(),
        )
        services()["course_service"].create_course(course)
        flash(f"Course '{course.code}' created.", "success")
    except (ValidationError, ValueError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<code>/edit", methods=["POST"])
def edit_course(code):
    course_service = services()["course_service"]
    try:
        course = course_service.get_course(code)
        if course is None:
            raise CourseNotFoundError(f"Course '{code}' not found")
        course.name = request.form.get("name", "").strip()
        course.description = request.form.get("description", "").strip()
        course.duration = int(request.form.get("duration", 0) or 0)
        course.difficulty = DifficultyLevel[request.form.get("difficulty", course.difficulty.name)]
        course_service.update_course(course)
        flash(f"Course '{code}' updated.", "success")
    except (ValidationError, CourseNotFoundError, ValueError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<code>/delete", methods=["POST"])
def delete_course(code):
    try:
        services()["course_service"].delete_course(code)
        flash(f"Course '{code}' deleted.", "success")
    except CourseNotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<code>/publish", methods=["POST"])
def publish_course(code):
    try:
        services()["course_service"].publish_course(code)
        flash(f"Course '{code}' published.", "success")
    except (CourseNotFoundError, ValidationError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<code>/archive", methods=["POST"])
def archive_course(code):
    try:
        services()["course_service"].archive_course(code)
        flash(f"Course '{code}' archived.", "success")
    except (CourseNotFoundError, ValidationError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.courses"))


# ── Course approvals (instructor submissions) ────────────────────────────────

@admin_bp.route("/course-approvals")
def course_approvals():
    db = services()["database"]
    status_filter = request.args.get("status", "PENDING")
    with db.get_connection() as conn:
        if status_filter == "ALL":
            rows = conn.execute(
                "SELECT * FROM course_submissions ORDER BY submitted_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM course_submissions WHERE status = ? ORDER BY submitted_at DESC",
                (status_filter,),
            ).fetchall()
    submissions = [dict(r) for r in rows]
    course_service = services()["course_service"]
    for s in submissions:
        s["course"] = course_service.get_course(s["course_code"])
    return render_template("admin/course_approvals.html", submissions=submissions, status_filter=status_filter)


@admin_bp.route("/course-approvals/<int:submission_id>/approve", methods=["POST"])
def approve_course_submission(submission_id):
    note = request.form.get("note", "").strip()
    svc = services()
    db = svc["database"]
    with db.get_connection() as conn:
        row = conn.execute("SELECT * FROM course_submissions WHERE id = ?", (submission_id,)).fetchone()
    if row is None:
        flash("Submission not found.", "error")
        return redirect(url_for("admin.course_approvals"))

    try:
        svc["course_service"].publish_course(row["course_code"])
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with db.transaction() as conn:
            conn.execute(
                "UPDATE course_submissions SET status='APPROVED', admin_note=?, decided_at=? WHERE id=?",
                (note, now, submission_id),
            )
        notif_repo = svc.get("notification_repo")
        if notif_repo:
            notif_repo.create(Notification(
                user_id=row["instructor_id"],
                message=(
                    f"Your course '{row['course_code']}' has been APPROVED and published."
                    + (f" Admin note: {note}" if note else "")
                ),
            ))
        flash(f"Course '{row['course_code']}' approved and published.", "success")
    except (CourseNotFoundError, ValidationError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.course_approvals"))


@admin_bp.route("/course-approvals/<int:submission_id>/reject", methods=["POST"])
def reject_course_submission(submission_id):
    note = request.form.get("note", "").strip()
    svc = services()
    db = svc["database"]
    with db.get_connection() as conn:
        row = conn.execute("SELECT * FROM course_submissions WHERE id = ?", (submission_id,)).fetchone()
    if row is None:
        flash("Submission not found.", "error")
        return redirect(url_for("admin.course_approvals"))
    if not note:
        flash("A rejection note is required.", "error")
        return redirect(url_for("admin.course_approvals"))

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with db.transaction() as conn:
        conn.execute(
            "UPDATE course_submissions SET status='REJECTED', admin_note=?, decided_at=? WHERE id=?",
            (note, now, submission_id),
        )
    notif_repo = svc.get("notification_repo")
    if notif_repo:
        notif_repo.create(Notification(
            user_id=row["instructor_id"],
            message=f"Your course '{row['course_code']}' submission was rejected. Admin feedback: {note}",
        ))
    flash(f"Submission for '{row['course_code']}' rejected.", "success")
    return redirect(url_for("admin.course_approvals"))


# ── Prerequisites ─────────────────────────────────────────────────────────────

@admin_bp.route("/prerequisites")
def prerequisites():
    course_service = services()["course_service"]
    all_courses = course_service.get_all_courses()
    selected_code = request.args.get("course")
    prereqs = []
    if selected_code:
        prereqs = sorted(course_service.get_prerequisites(selected_code))
    levels = course_service.get_course_levels()
    return render_template(
        "admin/prerequisites.html", courses=all_courses,
        selected_code=selected_code, prereqs=prereqs, levels=levels,
    )


@admin_bp.route("/prerequisites/add", methods=["POST"])
def add_prerequisite():
    course_code = request.form.get("course_code")
    prereq_code = request.form.get("prereq_code")
    try:
        services()["course_service"].add_prerequisite(course_code, prereq_code)
        flash("Prerequisite added.", "success")
    except (CourseNotFoundError, CircularDependencyError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.prerequisites", course=course_code))


@admin_bp.route("/prerequisites/remove", methods=["POST"])
def remove_prerequisite():
    course_code = request.form.get("course_code")
    prereq_code = request.form.get("prereq_code")
    services()["course_service"].remove_prerequisite(course_code, prereq_code)
    flash("Prerequisite removed.", "success")
    return redirect(url_for("admin.prerequisites", course=course_code))


# ── Learners ──────────────────────────────────────────────────────────────────

@admin_bp.route("/learners")
def learners():
    svc = services()
    learner_repo = svc["learner_repo"]
    progress_service = svc["progress_service"]
    all_learners = learner_repo.get_all_learners() if hasattr(learner_repo, "get_all_learners") else []
    rows = []
    for learner in all_learners:
        summary = progress_service.get_overall_summary(learner.id)
        rows.append({"learner": learner, "summary": summary})
    return render_template("admin/learners.html", rows=rows)


@admin_bp.route("/learners/create", methods=["POST"])
def create_learner():
    svc = services()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    try:
        new_user = svc["auth_service"].register(username, password, UserRole.LEARNER)
        svc["learner_repo"].create_learner(Learner(name=name, email=email, user_id=new_user.id))
        flash(f"Learner '{username}' created.", "success")
    except ValidationError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.learners"))


@admin_bp.route("/learners/<int:learner_id>/transfer-credit", methods=["POST"])
def transfer_credit(learner_id):
    course_code = request.form.get("course_code", "").strip().upper()
    note = request.form.get("note", "")
    try:
        result = services()["enrollment_service"].transfer_credit(learner_id, course_code, admin_note=note)
        flash(result.message or "Transfer credit granted.", "success" if result.success else "error")
    except (LearnerNotFoundError, CourseNotFoundError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.learners"))


@admin_bp.route("/learners/<int:learner_id>/approve-exemption", methods=["POST"])
def approve_exemption(learner_id):
    course_code = request.form.get("course_code", "").strip().upper()
    note = request.form.get("note", "")
    try:
        result = services()["enrollment_service"].approve_exemption(learner_id, course_code, admin_note=note)
        flash(result.message or "Exemption approved.", "success" if result.success else "error")
    except (LearnerNotFoundError, CourseNotFoundError) as e:
        flash(str(e), "error")
    return redirect(url_for("admin.learners"))


# ── Prior learning (final decision) ──────────────────────────────────────────

@admin_bp.route("/plr")
def plr():
    svc = services()
    filter_ = request.args.get("filter", "awaiting")
    if filter_ == "awaiting":
        requests_ = svc["prior_learning_service"].get_pending_admin_decision()
    else:
        requests_ = svc["prior_learning_service"].get_all_requests()
    learner_repo = svc["learner_repo"]
    for r in requests_:
        learner = learner_repo.get_learner(r.learner_id)
        r.learner_name = learner.name if learner else f"#{r.learner_id}"
    return render_template("admin/plr.html", requests=requests_, filter_=filter_)


@admin_bp.route("/plr/<int:request_id>/decide", methods=["POST"])
def plr_decide(request_id):
    from core.prior_learning_request import PLRStatus
    decision = request.form.get("decision")
    note = request.form.get("note", "").strip()
    try:
        status = PLRStatus.APPROVED if decision == "APPROVE" else PLRStatus.REJECTED
        services()["prior_learning_service"].admin_decision(request_id, status, note, admin_id=_admin_id())
        flash("Decision recorded.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.plr"))
