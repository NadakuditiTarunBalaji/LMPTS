import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, g

from core.enums import UserRole, DifficultyLevel, CourseStatus
from core.exceptions import ValidationError, CourseNotFoundError, LearnerNotFoundError
from core.course import Course

from webapp.auth_utils import services, role_required

instructor_bp = Blueprint("instructor", __name__, url_prefix="/instructor")


@instructor_bp.before_request
@role_required(UserRole.INSTRUCTOR)
def _guard():
    pass


@instructor_bp.route("/")
def dashboard():
    svc = services()
    my_courses = svc["course_service"].get_all_courses()
    plr_pending = svc["prior_learning_service"].get_pending_instructor_review()
    notifications = svc["notification_repo"].get_for_user(g.user.id)
    return render_template(
        "instructor/dashboard.html", courses=my_courses,
        plr_pending=plr_pending, notifications=notifications,
    )


@instructor_bp.route("/notifications/mark-read", methods=["POST"])
def mark_notifications_read():
    services()["notification_repo"].mark_all_read(g.user.id)
    return redirect(url_for("instructor.dashboard"))


# ── Courses ───────────────────────────────────────────────────────────────────

@instructor_bp.route("/courses")
def courses():
    svc = services()
    all_courses = svc["course_service"].get_all_courses()
    db = svc["database"]
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT course_code, status FROM course_submissions WHERE instructor_id = ? "
            "ORDER BY submitted_at DESC", (g.user.id,)
        ).fetchall()
    submission_status = {}
    for r in rows:
        submission_status.setdefault(r["course_code"], r["status"])
    return render_template(
        "instructor/courses.html", courses=all_courses,
        submission_status=submission_status, difficulties=list(DifficultyLevel),
    )


@instructor_bp.route("/courses/create", methods=["POST"])
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
        flash(f"Course '{course.code}' saved as DRAFT.", "success")
    except (ValidationError, ValueError) as e:
        flash(str(e), "error")
    return redirect(url_for("instructor.courses"))


@instructor_bp.route("/courses/<code>/edit", methods=["POST"])
def edit_course(code):
    course_service = services()["course_service"]
    try:
        course = course_service.get_course(code)
        if course is None:
            raise CourseNotFoundError(f"Course '{code}' not found")
        if course.status != CourseStatus.DRAFT:
            flash("Only DRAFT courses can be edited.", "error")
            return redirect(url_for("instructor.courses"))
        course.name = request.form.get("name", "").strip()
        course.description = request.form.get("description", "").strip()
        course.duration = int(request.form.get("duration", 0) or 0)
        course.difficulty = DifficultyLevel[request.form.get("difficulty", course.difficulty.name)]
        course_service.update_course(course)
        flash(f"Course '{code}' updated.", "success")
    except (ValidationError, CourseNotFoundError, ValueError) as e:
        flash(str(e), "error")
    return redirect(url_for("instructor.courses"))


@instructor_bp.route("/courses/<code>/delete", methods=["POST"])
def delete_course(code):
    course_service = services()["course_service"]
    course = course_service.get_course(code)
    if course and course.status != CourseStatus.DRAFT:
        flash("Only DRAFT courses can be deleted.", "error")
        return redirect(url_for("instructor.courses"))
    try:
        course_service.delete_course(code)
        flash(f"Draft '{code}' deleted.", "success")
    except CourseNotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("instructor.courses"))


@instructor_bp.route("/courses/<code>/submit", methods=["POST"])
def submit_for_review(code):
    svc = services()
    course_service = svc["course_service"]
    course = course_service.get_course(code)
    if course is None:
        flash("Course not found.", "error")
        return redirect(url_for("instructor.courses"))
    if course.status != CourseStatus.DRAFT:
        flash("Only DRAFT courses can be submitted for review.", "error")
        return redirect(url_for("instructor.courses"))

    db = svc["database"]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO course_submissions (course_code, instructor_id, status, instructor_note, submitted_at) "
            "VALUES (?, ?, 'PENDING', '', ?)",
            (code, g.user.id, now),
        )

    from core.notification import Notification
    notif_repo = svc.get("notification_repo")
    if notif_repo:
        for admin in svc["user_repo"].find_by_role(UserRole.ADMIN):
            notif_repo.create(Notification(
                user_id=admin.id,
                message=f"Instructor '{g.user.username}' submitted course '{code}' for review.",
            ))
    flash(f"'{code}' submitted for admin review.", "success")
    return redirect(url_for("instructor.courses"))


# ── Monitor learners ──────────────────────────────────────────────────────────

@instructor_bp.route("/learners")
def learners():
    svc = services()
    learner_repo = svc["learner_repo"]
    all_learners = learner_repo.get_all_learners()
    selected_id = request.args.get("learner_id", type=int)
    enrollments = []
    if selected_id:
        enrollments = svc["enrollment_service"].get_learner_enrollments(selected_id)
    return render_template(
        "instructor/learners.html", learners=all_learners,
        selected_id=selected_id, enrollments=enrollments,
    )


@instructor_bp.route("/learners/<int:learner_id>/<code>/start", methods=["POST"])
def start_enrollment(learner_id, code):
    try:
        services()["enrollment_service"].start_enrollment(learner_id, code)
        flash("Marked in progress.", "success")
    except LearnerNotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("instructor.learners", learner_id=learner_id))


@instructor_bp.route("/learners/<int:learner_id>/<code>/complete", methods=["POST"])
def complete_enrollment(learner_id, code):
    score = request.form.get("score", type=float)
    try:
        services()["enrollment_service"].complete_enrollment(learner_id, code, score)
        flash("Marked complete.", "success")
    except (LearnerNotFoundError, ValidationError) as e:
        flash(str(e), "error")
    return redirect(url_for("instructor.learners", learner_id=learner_id))


# ── Prior learning review ─────────────────────────────────────────────────────

@instructor_bp.route("/plr")
def plr():
    svc = services()
    filter_ = request.args.get("filter", "pending")
    if filter_ == "pending":
        requests_ = svc["prior_learning_service"].get_pending_instructor_review()
    elif filter_ == "mine":
        requests_ = [r for r in svc["prior_learning_service"].get_all_requests() if r.instructor_id == g.user.id]
    else:
        requests_ = svc["prior_learning_service"].get_all_requests()
    learner_repo = svc["learner_repo"]
    for r in requests_:
        learner = learner_repo.get_learner(r.learner_id)
        r.learner_name = learner.name if learner else f"#{r.learner_id}"
    return render_template("instructor/plr.html", requests=requests_, filter_=filter_)


@instructor_bp.route("/plr/<int:request_id>/review", methods=["POST"])
def plr_review(request_id):
    recommendation = request.form.get("recommendation")
    note = request.form.get("note", "").strip()
    try:
        services()["prior_learning_service"].instructor_review(
            request_id, recommendation, note, instructor_id=g.user.id,
        )
        flash("Review submitted.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("instructor.plr"))
