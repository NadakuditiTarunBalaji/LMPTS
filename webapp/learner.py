from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort

from core.enums import UserRole
from core.exceptions import LearnerNotFoundError, CourseNotFoundError, ValidationError

from webapp.auth_utils import services, role_required, current_learner_id

learner_bp = Blueprint("learner", __name__, url_prefix="/learner")


@learner_bp.before_request
@role_required(UserRole.LEARNER)
def _guard():
    learner_id = current_learner_id()
    if learner_id is None:
        abort(403, "No learner profile linked to this account.")
    g.learner_id = learner_id


@learner_bp.route("/")
def dashboard():
    svc = services()
    learner_id = g.learner_id
    summary = svc["progress_service"].get_overall_summary(learner_id)
    enrollments = svc["enrollment_service"].get_learner_enrollments(learner_id)
    completed = set(svc["enrollment_service"].get_completed_courses(learner_id))
    active = set(svc["enrollment_service"].get_active_courses(learner_id))
    enrolled_codes = completed | active | {e.course_code for e in enrollments}
    available = [c for c in svc["course_service"].get_available_courses() if c.code not in enrolled_codes]
    return render_template(
        "learner/dashboard.html", summary=summary,
        enrollments=enrollments, available=available,
    )


@learner_bp.route("/enroll", methods=["POST"])
def enroll():
    code = request.form.get("course_code", "").strip().upper()
    try:
        result = services()["enrollment_service"].enroll_learner(g.learner_id, code)
        if result.success:
            flash(f"Enrolled in '{code}'.", "success")
        else:
            msg = result.message or "Enrollment failed."
            if result.missing_prerequisites:
                msg += f" Missing prerequisites: {', '.join(result.missing_prerequisites)}"
            flash(msg, "error")
    except (LearnerNotFoundError, CourseNotFoundError) as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("learner.dashboard"))


# ── Enrollments ───────────────────────────────────────────────────────────────

@learner_bp.route("/enrollments")
def enrollments():
    svc = services()
    status_filter = request.args.get("status", "ALL")
    all_enrollments = svc["enrollment_service"].get_learner_enrollments(g.learner_id)
    if status_filter != "ALL":
        all_enrollments = [e for e in all_enrollments if e.status.value == status_filter]
    return render_template("learner/enrollments.html", enrollments=all_enrollments, status_filter=status_filter)


@learner_bp.route("/enrollments/<code>/start", methods=["POST"])
def start_enrollment(code):
    try:
        services()["enrollment_service"].start_enrollment(g.learner_id, code)
        flash(f"Started '{code}'.", "success")
    except LearnerNotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("learner.enrollments"))


@learner_bp.route("/enrollments/<code>/complete", methods=["POST"])
def complete_enrollment(code):
    score = request.form.get("score", type=float)
    try:
        services()["enrollment_service"].complete_enrollment(g.learner_id, code, score)
        flash(f"Completed '{code}'.", "success")
    except (LearnerNotFoundError, ValidationError) as e:
        flash(str(e), "error")
    return redirect(url_for("learner.enrollments"))


@learner_bp.route("/enrollments/<code>/cancel", methods=["POST"])
def cancel_enrollment(code):
    try:
        services()["enrollment_service"].cancel_enrollment(g.learner_id, code)
        flash(f"Cancelled '{code}'.", "success")
    except LearnerNotFoundError as e:
        flash(str(e), "error")
    return redirect(url_for("learner.enrollments"))


# ── Learning path ─────────────────────────────────────────────────────────────

@learner_bp.route("/path")
def path():
    svc = services()
    goal = request.args.get("goal")
    roadmap = None
    if goal:
        try:
            roadmap = svc["learning_path_service"].get_learner_roadmap(g.learner_id, goal)
        except (LearnerNotFoundError, CourseNotFoundError) as e:
            flash(str(e), "error")
    all_courses = svc["course_service"].get_all_courses()
    return render_template("learner/path.html", courses=all_courses, goal=goal, roadmap=roadmap)


# ── Progress ──────────────────────────────────────────────────────────────────

@learner_bp.route("/progress")
def progress():
    svc = services()
    summary = svc["progress_service"].get_overall_summary(g.learner_id)
    course_progress = svc["progress_service"].get_learner_progress(g.learner_id)
    return render_template("learner/progress.html", summary=summary, course_progress=course_progress)


# ── Prior learning ────────────────────────────────────────────────────────────

@learner_bp.route("/prior-learning")
def prior_learning():
    svc = services()
    requests_ = svc["prior_learning_service"].get_learner_requests(g.learner_id)
    all_courses = svc["course_service"].get_all_courses()
    return render_template("learner/prior_learning.html", requests=requests_, courses=all_courses)


@learner_bp.route("/prior-learning/submit", methods=["POST"])
def submit_prior_learning():
    course_code = request.form.get("course_code", "").strip().upper()
    pathway = request.form.get("pathway")
    evidence = request.form.get("evidence_description", "").strip()
    platform = request.form.get("external_platform", "").strip()
    score_raw = request.form.get("external_score", "").strip()
    score = float(score_raw) if score_raw else None

    try:
        svc = services()
        svc["prior_learning_service"].submit_request(
            learner_id=g.learner_id, course_code=course_code, pathway=pathway,
            evidence_description=evidence, external_platform=platform, external_score=score,
        )
        flash("Prior learning request submitted.", "success")
    except (LearnerNotFoundError, CourseNotFoundError, ValueError) as e:
        flash(str(e), "error")
    return redirect(url_for("learner.prior_learning"))


# ── Recommendations ───────────────────────────────────────────────────────────

@learner_bp.route("/recommendations")
def recommendations():
    svc = services()
    difficulty = request.args.get("difficulty", "BEGINNER")
    try:
        recs = svc["recommendation_service"].get_recommendations(g.learner_id, difficulty_preference=difficulty)
    except LearnerNotFoundError as e:
        flash(str(e), "error")
        recs = []
    return render_template("learner/recommendations.html", recommendations=recs, difficulty=difficulty)
