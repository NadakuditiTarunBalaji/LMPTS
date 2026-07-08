"""
test_analytics_service.py
-------------------------
Tests for AnalyticsService.
"""

import pytest
from core.user import User
from core.course import Course
from core.learner import Learner
from core.enums import UserRole, DifficultyLevel, CourseStatus
from algorithms.graph import CourseGraph
from repository.database import Database
from repository.user_repo import SQLiteUserRepository
from repository.course_repo import SQLiteCourseRepository
from repository.learner_repo import SQLiteLearnerRepository
from repository.enrollment_repo import (
    SQLiteEnrollmentRepository,
    SQLiteProgressRepository,
)
from repository.cancellation_request_repo import (
    SQLiteCancellationRequestRepository,
)
from services.course_service import CourseService
from services.enrollment_service import EnrollmentService
from services.analytics_service import AnalyticsService
from auth.password_manager import PasswordManager


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.initialize()
    return database


@pytest.fixture
def pm():
    return PasswordManager()


@pytest.fixture
def graph():
    return CourseGraph()


@pytest.fixture
def repos(db):
    return {
        "user":       SQLiteUserRepository(db),
        "course":     SQLiteCourseRepository(db),
        "learner":    SQLiteLearnerRepository(db),
        "enrollment": SQLiteEnrollmentRepository(db),
        "progress":   SQLiteProgressRepository(db),
        "cancellation_request": SQLiteCancellationRequestRepository(db),
    }


@pytest.fixture
def course_service(repos, graph):
    return CourseService(repos["course"], graph)


@pytest.fixture
def enrollment_service(repos, graph, db):
    return EnrollmentService(
        enrollment_repo = repos["enrollment"],
        progress_repo   = repos["progress"],
        learner_repo    = repos["learner"],
        course_repo     = repos["course"],
        cancellation_request_repo = repos["cancellation_request"],
        graph           = graph,
        database        = db,
    )


@pytest.fixture
def analytics_service(repos, graph):
    return AnalyticsService(
        enrollment_repo = repos["enrollment"],
        progress_repo   = repos["progress"],
        learner_repo    = repos["learner"],
        course_repo     = repos["course"],
        graph           = graph,
    )


@pytest.fixture
def setup_curriculum(course_service):
    """Create a standard test curriculum."""
    courses = [
        Course("CS101", "Intro", DifficultyLevel.BEGINNER, 20,
               status=CourseStatus.PUBLISHED),
        Course("CS102", "Math",  DifficultyLevel.BEGINNER, 25,
               status=CourseStatus.PUBLISHED),
        Course("CS201", "DS",    DifficultyLevel.INTERMEDIATE, 40,
               status=CourseStatus.PUBLISHED),
        Course("CS301", "Algo",  DifficultyLevel.ADVANCED, 60,
               status=CourseStatus.PUBLISHED),
    ]
    for c in courses:
        course_service.create_course(c)
    course_service.add_prerequisite("CS201", "CS101")
    course_service.add_prerequisite("CS201", "CS102")
    course_service.add_prerequisite("CS301", "CS201")
    return courses


@pytest.fixture
def setup_learner(repos, pm):
    user = repos["user"].create_user(
        User("alice", pm.hash_password("pass1234"), UserRole.LEARNER)
    )
    return repos["learner"].create_learner(
        Learner(name="Alice", email="alice@test.com", user_id=user.id)
    )


class TestCourseCompletionRate:

    def test_empty_enrollment(self, analytics_service, setup_curriculum):
        stats = analytics_service.course_completion_rate("CS101")
        assert stats["total_enrolled"]  == 0
        assert stats["completion_rate"] == 0.0

    def test_completion_rate_after_enrollment(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.complete_enrollment(
            setup_learner.id, "CS101", 90
        )
        stats = analytics_service.course_completion_rate("CS101")
        assert stats["total_enrolled"]  == 1
        assert stats["completed"]        == 1
        assert stats["completion_rate"] == 100.0


class TestMostEnrolledCourses:

    def test_returns_list(self, analytics_service, setup_curriculum):
        result = analytics_service.most_enrolled_courses()
        assert isinstance(result, list)

    def test_sorted_by_enrollment(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        result = analytics_service.most_enrolled_courses()
        assert result[0]["course_code"] == "CS101"
        assert result[0]["enrollments"] == 1

    def test_respects_limit(self, analytics_service, setup_curriculum):
        result = analytics_service.most_enrolled_courses(limit=2)
        assert len(result) <= 2


class TestBottleneckCourses:

    def test_no_bottlenecks_empty(
        self, analytics_service, setup_curriculum
    ):
        result = analytics_service.bottleneck_courses()
        assert result == []

    def test_identifies_high_dropout(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.cancel_enrollment(setup_learner.id, "CS101")
        result = analytics_service.bottleneck_courses(
            dropout_threshold=50.0
        )
        codes = [r["course_code"] for r in result]
        assert "CS101" in codes


class TestAverageScore:

    def test_no_completions(self, analytics_service, setup_curriculum):
        result = analytics_service.average_score_by_course()
        for item in result:
            assert item["average_score"] is None

    def test_average_calculated(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.complete_enrollment(
            setup_learner.id, "CS101", 80
        )
        result = analytics_service.average_score_by_course()
        cs101  = next(
            r for r in result if r["course_code"] == "CS101"
        )
        assert cs101["average_score"] == 80.0


class TestDifficultyDistribution:

    def test_distribution_counts(
        self, analytics_service, setup_curriculum
    ):
        dist = analytics_service.difficulty_distribution()
        assert dist["BEGINNER"]     == 2
        assert dist["INTERMEDIATE"] == 1
        assert dist["ADVANCED"]     == 1
        assert dist["total"]        == 4


class TestPrerequisiteChainLength:

    def test_chain_lengths(self, analytics_service, setup_curriculum):
        result = analytics_service.prerequisite_chain_length()
        codes  = {r["course_code"]: r for r in result}

        assert codes["CS101"]["chain_length"] == 0
        assert codes["CS201"]["chain_length"] == 2
        assert codes["CS301"]["chain_length"] == 3

    def test_sorted_by_chain_length(
        self, analytics_service, setup_curriculum
    ):
        result = analytics_service.prerequisite_chain_length()
        lengths = [r["chain_length"] for r in result]
        assert lengths == sorted(lengths, reverse=True)


class TestLearnerProgressSummary:

    def test_summary_structure(
        self, analytics_service, setup_learner
    ):
        summary = analytics_service.learner_progress_summary(
            setup_learner.id
        )
        assert "learner_id"      in summary
        assert "learner_name"    in summary
        assert "total_enrolled"  in summary
        assert "completed"       in summary
        assert "completion_rate" in summary
        assert "courses"         in summary

    def test_summary_after_enrollment(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.complete_enrollment(
            setup_learner.id, "CS101", 90
        )
        summary = analytics_service.learner_progress_summary(
            setup_learner.id
        )
        assert summary["total_enrolled"]  == 1
        assert summary["completed"]        == 1
        assert summary["completion_rate"] == 100.0
        assert summary["average_score"]   == 90.0


class TestSystemOverview:

    def test_system_overview_structure(
        self, analytics_service, setup_curriculum
    ):
        overview = analytics_service.system_overview()
        assert "total_courses"           in overview
        assert "total_learners"          in overview
        assert "total_enrollments"       in overview
        assert "overall_completion_rate" in overview
        assert "difficulty_distribution" in overview

    def test_system_overview_counts(
        self, analytics_service, setup_curriculum
    ):
        overview = analytics_service.system_overview()
        assert overview["total_courses"] == 4


class TestStudentPerformanceReport:

    def test_empty(self, analytics_service, setup_curriculum):
        assert analytics_service.student_performance_report() == []

    def test_row_after_completion(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.complete_enrollment(setup_learner.id, "CS101", 95)

        rows = analytics_service.student_performance_report()
        assert len(rows) == 1
        row = rows[0]
        assert row["student_name"] == "Alice"
        assert row["course_code"]  == "CS101"
        assert row["score"]        == 95
        assert row["grade"]        == "A"
        assert row["status"]       == "COMPLETED"


class TestScoreBucketDistribution:

    def test_empty(self, analytics_service, setup_curriculum):
        result = analytics_service.score_bucket_distribution()
        assert result == {
            "Excellent": 0, "Good": 0, "Average": 0, "Poor": 0, "total": 0
        }

    def test_bucket_after_completion(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.complete_enrollment(setup_learner.id, "CS101", 95)

        result = analytics_service.score_bucket_distribution()
        assert result["Excellent"] == 1
        assert result["total"]     == 1


class TestPerformanceTrend:

    def test_empty_has_no_gaps(self, analytics_service, setup_curriculum):
        result = analytics_service.performance_trend(months=3)
        assert len(result) == 3
        assert all(r["average_score"] is None for r in result)

    def test_current_month_average(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.complete_enrollment(setup_learner.id, "CS101", 80)

        result = analytics_service.performance_trend(months=3)
        assert result[-1]["average_score"] == 80.0
        assert result[-1]["completions"]   == 1


class TestCourseCompletionBreakdown:

    def test_empty(self, analytics_service, setup_curriculum):
        result = analytics_service.course_completion_breakdown()
        assert result["total"]           == 0
        assert result["completion_rate"] == 0.0

    def test_after_completion(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.complete_enrollment(setup_learner.id, "CS101", 80)

        result = analytics_service.course_completion_breakdown()
        assert result["completed"]       == 1
        assert result["completion_rate"] == 100.0


class TestCourseCompletionByCourse:

    def test_empty(self, analytics_service, setup_curriculum):
        result = analytics_service.course_completion_by_course()
        assert result["labels"] == []

    def test_after_completion(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.complete_enrollment(setup_learner.id, "CS101", 80)

        result = analytics_service.course_completion_by_course()
        assert "Intro" in result["labels"]
        idx = result["labels"].index("Intro")
        assert result["completed"][idx] == 1


class TestEnrollmentMonthlyTrend:

    def test_empty_has_no_gaps(self, analytics_service, setup_curriculum):
        result = analytics_service.enrollment_monthly_trend(months=3)
        assert len(result) == 3
        assert all(r["count"] == 0 for r in result)

    def test_current_month_count(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        result = analytics_service.enrollment_monthly_trend(months=3)
        assert result[-1]["count"] == 1


class TestEnrollmentSummaryMetrics:

    def test_empty(self, analytics_service, setup_curriculum):
        result = analytics_service.enrollment_summary_metrics()
        assert result["total_enrollments"]   == 0
        assert result["new_this_week"]       == 0
        assert result["monthly_enrollments"] == 0
        assert result["growth_rate"]         == 0.0

    def test_after_enrollment(
        self, analytics_service, enrollment_service,
        setup_curriculum, setup_learner
    ):
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        result = analytics_service.enrollment_summary_metrics()
        assert result["total_enrollments"]   == 1
        assert result["new_this_week"]       == 1
        assert result["monthly_enrollments"] == 1
        assert result["growth_rate"]         == 100.0


class TestInstructorAnalytics:

    def test_empty_instructors(self, analytics_service):
        assert analytics_service.instructor_analytics([], {}) == []

    def test_instructor_with_no_courses(self, analytics_service, repos, pm):
        instructor = repos["user"].create_user(
            User("bob", pm.hash_password("pass1234"), UserRole.INSTRUCTOR)
        )
        result = analytics_service.instructor_analytics([instructor], {})
        assert len(result) == 1
        assert result[0]["courses_created"]   == 0
        assert result[0]["students_assigned"] == 0
        assert result[0]["completion_rate"]   == 0.0
        assert result[0]["average_rating"]    == "N/A"

    def test_instructor_with_courses_and_students(
        self, analytics_service, enrollment_service, repos, pm,
        setup_curriculum, setup_learner
    ):
        instructor = repos["user"].create_user(
            User("bob", pm.hash_password("pass1234"), UserRole.INSTRUCTOR)
        )
        enrollment_service.enroll_learner(setup_learner.id, "CS101")
        enrollment_service.complete_enrollment(setup_learner.id, "CS101", 80)

        result = analytics_service.instructor_analytics(
            [instructor], {instructor.id: {"CS101"}}
        )
        assert result[0]["courses_created"]   == 1
        assert result[0]["students_assigned"] == 1
        assert result[0]["completion_rate"]   == 100.0
        assert result[0]["average_rating"]    == "N/A"