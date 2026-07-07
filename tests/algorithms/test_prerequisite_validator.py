"""
test_prerequisite_validator.py
-------------------------------
Tests for PrerequisiteValidator — enrollment eligibility.
"""

import pytest
from algorithms.graph import CourseGraph
from algorithms.prerequisite_validator import (
    PrerequisiteValidator,
    LearnerCredits,
    CreditType,
)


@pytest.fixture
def graph():
    """
    CS101 → CS201 → CS301
    CS102 → CS201
    """
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS102", "CS201")
    g.add_edge("CS201", "CS301")
    return g


@pytest.fixture
def validator(graph):
    return PrerequisiteValidator(graph)


class TestCanEnroll:

    def test_no_prerequisites_allowed(self, validator):
        credits = LearnerCredits()
        result  = validator.can_enroll(credits, "CS101")
        assert result.can_enroll is True

    def test_direct_prerequisite_satisfied(self, validator):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        result  = validator.can_enroll(credits, "CS201")
        assert result.can_enroll is True

    def test_direct_prerequisite_missing(self, validator):
        credits = LearnerCredits(completed={"CS101"})
        result  = validator.can_enroll(credits, "CS201")
        assert result.can_enroll is False
        assert "CS102" in result.missing_prerequisites

    def test_all_prerequisites_missing(self, validator):
        credits = LearnerCredits()
        result  = validator.can_enroll(credits, "CS201")
        assert result.can_enroll is False
        assert len(result.missing_prerequisites) == 2

    def test_transfer_credit_satisfies_prereq(self, validator):
        credits = LearnerCredits(
            transfer_credits={"CS101", "CS102"}
        )
        result = validator.can_enroll(credits, "CS201")
        assert result.can_enroll is True

    def test_exemption_satisfies_prereq(self, validator):
        credits = LearnerCredits(
            exemptions={"CS101", "CS102"}
        )
        result = validator.can_enroll(credits, "CS201")
        assert result.can_enroll is True

    def test_placement_test_satisfies_prereq(self, validator):
        credits = LearnerCredits(
            placement_tests={"CS101", "CS102"}
        )
        result = validator.can_enroll(credits, "CS201")
        assert result.can_enroll is True

    def test_mixed_credit_types(self, validator):
        """One prereq by completion, one by transfer"""
        credits = LearnerCredits(
            completed={"CS101"},
            transfer_credits={"CS102"},
        )
        result = validator.can_enroll(credits, "CS201")
        assert result.can_enroll is True

    def test_course_not_in_graph(self, validator):
        credits = LearnerCredits()
        result  = validator.can_enroll(credits, "UNKNOWN")
        assert result.can_enroll is False
        assert "not found" in result.message.lower()

    def test_result_message_on_failure(self, validator):
        credits = LearnerCredits()
        result  = validator.can_enroll(credits, "CS201")
        assert "Missing" in result.message or "missing" in result.message

    def test_result_message_on_success(self, validator):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        result  = validator.can_enroll(credits, "CS201")
        assert "allowed" in result.message.lower()

    def test_bool_true(self, validator):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        result  = validator.can_enroll(credits, "CS201")
        assert bool(result) is True

    def test_bool_false(self, validator):
        credits = LearnerCredits()
        result  = validator.can_enroll(credits, "CS201")
        assert bool(result) is False


class TestCanEnrollFullChain:

    def test_full_chain_all_satisfied(self, validator):
        credits = LearnerCredits(completed={"CS101", "CS102", "CS201"})
        result  = validator.can_enroll_full_chain(credits, "CS301")
        assert result.can_enroll is True

    def test_full_chain_missing_transitive(self, validator):
        """CS201 completed but CS101, CS102 not — full chain fails"""
        credits = LearnerCredits(completed={"CS201"})
        result  = validator.can_enroll_full_chain(credits, "CS301")
        assert result.can_enroll is False
        missing = set(result.missing_prerequisites)
        assert "CS101" in missing or "CS102" in missing

    def test_direct_vs_full_chain_difference(self, validator):
        """Direct check passes, full chain fails"""
        credits = LearnerCredits(completed={"CS201"})

        direct_result = validator.can_enroll(credits, "CS301")
        full_result   = validator.can_enroll_full_chain(credits, "CS301")

        assert direct_result.can_enroll is True
        assert full_result.can_enroll   is False


class TestSatisfiedBy:

    def test_satisfied_by_normal(self, validator):
        credits = LearnerCredits(
            completed={"CS101", "CS102"}
        )
        result = validator.can_enroll(credits, "CS201")
        assert result.satisfied_by.get("CS101") == CreditType.NORMAL
        assert result.satisfied_by.get("CS102") == CreditType.NORMAL

    def test_satisfied_by_transfer(self, validator):
        credits = LearnerCredits(
            transfer_credits={"CS101", "CS102"}
        )
        result = validator.can_enroll(credits, "CS201")
        assert result.satisfied_by.get("CS101") == CreditType.TRANSFER

    def test_satisfied_by_exemption(self, validator):
        credits = LearnerCredits(
            exemptions={"CS101", "CS102"}
        )
        result = validator.can_enroll(credits, "CS201")
        assert result.satisfied_by.get("CS101") == CreditType.EXEMPTION


class TestWhatCanEnroll:

    def test_no_credits(self, validator):
        credits    = LearnerCredits()
        enrollable = validator.what_can_enroll(credits)
        # Only courses with no prerequisites
        assert "CS101" in enrollable
        assert "CS102" in enrollable
        assert "CS201" not in enrollable

    def test_after_completing_prerequisites(self, validator):
        credits    = LearnerCredits(completed={"CS101", "CS102"})
        enrollable = validator.what_can_enroll(credits)
        assert "CS201" in enrollable

    def test_satisfied_excluded(self, validator):
        credits    = LearnerCredits(completed={"CS101"})
        enrollable = validator.what_can_enroll(credits)
        # CS101 itself should not appear
        assert "CS101" not in enrollable


class TestCanAddPrerequisite:

    def test_safe_addition(self, validator):
        assert validator.can_add_prerequisite("CS201", "CS102") is True

    def test_would_create_cycle(self, validator):
        # CS301 → CS201 → CS301 cycle
        assert validator.can_add_prerequisite("CS101", "CS301") is False

    def test_self_prerequisite_not_allowed(self, validator):
        assert validator.can_add_prerequisite("CS101", "CS101") is False


class TestLearnerCredits:

    def test_all_satisfied_union(self):
        credits = LearnerCredits(
            completed={"A"},
            transfer_credits={"B"},
            exemptions={"C"},
            placement_tests={"D"},
        )
        assert credits.all_satisfied == {"A", "B", "C", "D"}

    def test_empty_credits(self):
        credits = LearnerCredits()
        assert credits.all_satisfied == set()