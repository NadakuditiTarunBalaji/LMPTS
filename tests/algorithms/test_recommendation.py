"""
test_recommendation.py
-----------------------
Tests for RecommendationEngine.
"""

import pytest
from algorithms.graph import CourseGraph
from algorithms.recommendation import RecommendationEngine, CourseInfo
from algorithms.prerequisite_validator import LearnerCredits


@pytest.fixture
def graph():
    """
    CS101 → CS201 → CS301
    CS102 → CS201
    PY101 → PY201
    """
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS102", "CS201")
    g.add_edge("CS201", "CS301")
    g.add_edge("PY101", "PY201")
    return g


@pytest.fixture
def course_info():
    return {
        "CS101": CourseInfo("CS101", "Intro to CS",
                            "BEGINNER", 20),
        "CS102": CourseInfo("CS102", "Math for CS",
                            "BEGINNER", 25),
        "CS201": CourseInfo("CS201", "Data Structures",
                            "INTERMEDIATE", 40),
        "CS301": CourseInfo("CS301", "Algorithms",
                            "ADVANCED", 60),
        "PY101": CourseInfo("PY101", "Python Basics",
                            "BEGINNER", 15),
        "PY201": CourseInfo("PY201", "Python Advanced",
                            "INTERMEDIATE", 35),
    }


@pytest.fixture
def engine(graph):
    return RecommendationEngine(graph)


class TestRecommend:

    def test_returns_list(self, engine, course_info):
        credits = LearnerCredits()
        recs    = engine.recommend(credits, course_info)
        assert isinstance(recs, list)

    def test_no_credits_recommends_entry_courses(
        self, engine, course_info
    ):
        credits = LearnerCredits()
        recs    = engine.recommend(credits, course_info)
        codes   = [r.course_code for r in recs]
        # Only courses with no prerequisites
        assert "CS101" in codes or "CS102" in codes or "PY101" in codes
        assert "CS201" not in codes  # needs CS101 + CS102
        assert "CS301" not in codes  # needs CS201

    def test_respects_limit(self, engine, course_info):
        credits = LearnerCredits()
        recs    = engine.recommend(credits, course_info, limit=2)
        assert len(recs) <= 2

    def test_sorted_by_score_descending(self, engine, course_info):
        credits = LearnerCredits()
        recs    = engine.recommend(credits, course_info)
        scores  = [r.score for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_completed_courses_excluded(self, engine, course_info):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        recs    = engine.recommend(credits, course_info)
        codes   = [r.course_code for r in recs]
        assert "CS101" not in codes
        assert "CS102" not in codes

    def test_transfer_credits_unlock_courses(self, engine, course_info):
        credits = LearnerCredits(transfer_credits={"CS101", "CS102"})
        recs    = engine.recommend(credits, course_info)
        codes   = [r.course_code for r in recs]
        assert "CS201" in codes

    def test_difficulty_preference_beginner(self, engine, course_info):
        """Beginner courses should score higher when preference=BEGINNER"""
        credits = LearnerCredits()
        recs    = engine.recommend(
            credits, course_info,
            difficulty_preference="BEGINNER"
        )
        if recs:
            # Top recommendation should be beginner level
            top = recs[0]
            info = course_info.get(top.course_code)
            if info:
                assert info.difficulty in ["BEGINNER", "INTERMEDIATE"]

    def test_exclude_parameter(self, engine, course_info):
        credits = LearnerCredits()
        recs    = engine.recommend(
            credits, course_info,
            exclude={"CS101"}
        )
        codes = [r.course_code for r in recs]
        assert "CS101" not in codes

    def test_recommendation_has_reasons(self, engine, course_info):
        credits = LearnerCredits()
        recs    = engine.recommend(credits, course_info)
        if recs:
            assert len(recs[0].reasons) > 0

    def test_recommendation_score_range(self, engine, course_info):
        credits = LearnerCredits()
        recs    = engine.recommend(credits, course_info)
        for rec in recs:
            assert 0 <= rec.score <= 100

    def test_empty_graph(self, course_info):
        g      = CourseGraph()
        engine = RecommendationEngine(g)
        recs   = engine.recommend(LearnerCredits(), course_info)
        assert recs == []

    def test_all_completed_no_recommendations(
        self, engine, course_info, graph
    ):
        all_courses = set(graph.get_courses())
        credits     = LearnerCredits(completed=all_courses)
        recs        = engine.recommend(credits, course_info)
        assert recs == []


class TestGetLearningRoadmap:

    def test_roadmap_single_goal(self, engine, course_info):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        roadmap = engine.get_learning_roadmap(
            learner_credits=credits,
            goal_courses=["CS301"],
            course_info=course_info,
        )
        assert "CS301" in roadmap
        assert "CS201" in roadmap["CS301"]
        assert "CS101" not in roadmap["CS301"]

    def test_roadmap_transfer_credit(self, engine, course_info):
        credits = LearnerCredits(
            transfer_credits={"CS101", "CS102", "CS201"}
        )
        roadmap = engine.get_learning_roadmap(
            learner_credits=credits,
            goal_courses=["CS301"],
            course_info=course_info,
        )
        assert roadmap["CS301"] == ["CS301"]

    def test_roadmap_empty_when_goal_satisfied(
        self, engine, course_info
    ):
        credits = LearnerCredits(
            completed={"CS101", "CS102", "CS201", "CS301"}
        )
        roadmap = engine.get_learning_roadmap(
            learner_credits=credits,
            goal_courses=["CS301"],
            course_info=course_info,
        )
        assert roadmap["CS301"] == []