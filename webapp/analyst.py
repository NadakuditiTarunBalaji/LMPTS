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
    svc = services()["analytics_service"]
    overview = svc.system_overview()
    distribution = svc.difficulty_distribution()
    most_enrolled = svc.most_enrolled_courses(limit=5)
    return render_template("analyst/dashboard.html", overview=overview, distribution=distribution, most_enrolled=most_enrolled)


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
