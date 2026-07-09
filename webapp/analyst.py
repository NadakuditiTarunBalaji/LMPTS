from collections import defaultdict

from flask import Blueprint, render_template, request

from core.enums import UserRole

from webapp.auth_utils import services, role_required

analyst_bp = Blueprint("analyst", __name__, url_prefix="/analyst")


@analyst_bp.before_request
@role_required(UserRole.ANALYST, UserRole.ADMIN)
def _guard():
    pass


@analyst_bp.route("/")
def dashboard():
<<<<<<< HEAD
    svc = services()["analytics_service"]
    overview = svc.system_overview()
    distribution = svc.difficulty_distribution()
    most_enrolled = svc.most_enrolled_courses(limit=5)
    return render_template("analyst/dashboard.html", overview=overview, distribution=distribution, most_enrolled=most_enrolled)
=======
    svc = services()
    analytics = svc["analytics_service"]

    overview = analytics.system_overview()

    # Section 2 — Student Performance
    performance_report = analytics.student_performance_report()
    score_buckets = analytics.score_bucket_distribution()
    performance_trend = analytics.performance_trend(months=6)

    # Section 3 — Course Completion Analytics
    completion_breakdown = analytics.course_completion_breakdown()
    completion_by_course = analytics.course_completion_by_course()

    # Section 4 — Enrollment Analytics
    enrollment_metrics = analytics.enrollment_summary_metrics()
    enrollment_trend = analytics.enrollment_monthly_trend(months=6)

    # Section 5 — Instructor Analytics
    instructors = svc["user_repo"].find_by_role(UserRole.INSTRUCTOR)
    db = svc["database"]
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT instructor_id, course_code FROM course_submissions "
            "WHERE status != 'REJECTED'"
        ).fetchall()
    instructor_courses = defaultdict(set)
    for r in rows:
        instructor_courses[r["instructor_id"]].add(r["course_code"])
    instructor_report = analytics.instructor_analytics(instructors, instructor_courses)

    return render_template(
        "analyst/dashboard.html",
        overview=overview,
        performance_report=performance_report,
        score_buckets=score_buckets,
        performance_trend=performance_trend,
        completion_breakdown=completion_breakdown,
        completion_by_course=completion_by_course,
        enrollment_metrics=enrollment_metrics,
        enrollment_trend=enrollment_trend,
        instructor_report=instructor_report,
    )
>>>>>>> d8e71ef3f647a61b2f54c19b01cf8448ef9c2aac


@analyst_bp.route("/courses")
def courses():
    svc = services()["analytics_service"]
    most_enrolled = svc.most_enrolled_courses(limit=50)
    rows = []
    for c in most_enrolled:
        stats = svc.course_completion_rate(c["course_code"])
        rows.append({**c, **stats})
    return render_template("analyst/courses.html", rows=rows)


@analyst_bp.route("/learners")
def learners():
    report = services()["analytics_service"].learner_activity_report()
    return render_template("analyst/learners.html", report=report)


@analyst_bp.route("/completion-stats")
def completion_stats():
    chains = services()["analytics_service"].prerequisite_chain_length()
    return render_template("analyst/completion_stats.html", chains=chains)


@analyst_bp.route("/bottlenecks")
def bottlenecks():
    threshold = request.args.get("threshold", 30.0, type=float)
    bottlenecks_ = services()["analytics_service"].bottleneck_courses(dropout_threshold=threshold)
    return render_template("analyst/bottlenecks.html", bottlenecks=bottlenecks_, threshold=threshold)
