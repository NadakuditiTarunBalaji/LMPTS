"""
exceptions.py
-------------
Complete exception hierarchy for the LMPTS system.

UML Class Diagram – Exception Hierarchy:

    Exception
        └── LMPTSException
                ├── ValidationError
                ├── AuthenticationError
                ├── CourseNotFoundError
                ├── LearnerNotFoundError
                ├── EnrollmentError
                │       ├── DuplicateEnrollmentError
                │       └── PrerequisiteNotMetError
                └── CircularDependencyError

UML Prerequisite Graph (Section 11):
    CircularDependencyError is raised when DFS detects a cycle
    in the course prerequisite graph.

Every custom exception inherits from LMPTSException so callers
can catch broadly or precisely.
"""


class LMPTSException(Exception):
    """
    Base class for ALL LMPTS application errors.

    UML: Root of the exception hierarchy.

    Usage:
        try:
            risky_operation()
        except LMPTSException as e:
            log_error(e)   # catches any LMPTS error
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationError(LMPTSException):
    """
    Raised when input data fails business-rule validation.

    Examples:
        - Username is empty
        - Password shorter than 8 characters
        - Course duration is zero or negative
        - Email format invalid

    UML: Direct child of LMPTSException

    Usage:
        if not username.strip():
            raise ValidationError("Username cannot be empty")
    """


# ── Authentication ────────────────────────────────────────────────────────────

class AuthenticationError(LMPTSException):
    """
    Raised when login credentials are invalid or session is missing.

    UML Sequence Diagram (Section 5):
        Step 6 alt: PasswordManager returns False
        → AuthenticationError raised

    Usage:
        raise AuthenticationError("Invalid username or password")
    """


# ── Resource Not Found ────────────────────────────────────────────────────────

class CourseNotFoundError(LMPTSException):
    """
    Raised when a course code does not exist in the system.

    UML: Direct child of LMPTSException

    Usage:
        raise CourseNotFoundError(f"Course '{code}' does not exist")
    """


class LearnerNotFoundError(LMPTSException):
    """
    Raised when a learner ID or email cannot be resolved.

    UML: Direct child of LMPTSException

    Usage:
        raise LearnerNotFoundError(f"Learner {learner_id} not found")
    """


# ── Enrollment ────────────────────────────────────────────────────────────────

class EnrollmentError(LMPTSException):
    """
    Base class for all enrollment-related errors.

    UML: Parent of DuplicateEnrollmentError and PrerequisiteNotMetError

    Catch this to handle any enrollment problem broadly:
        except EnrollmentError as e:
            show_enrollment_error(e)
    """


class DuplicateEnrollmentError(EnrollmentError):
    """
    Raised when a learner tries to enroll in a course they
    are already enrolled in (status ENROLLED or IN_PROGRESS).

    UML Enrollment Sequence Diagram (Section 6):
        Step 4: "Duplicate check occurs"
        → If duplicate found, raise DuplicateEnrollmentError

    Usage:
        raise DuplicateEnrollmentError(
            "Learner 7 is already enrolled in CS201"
        )
    """


class PrerequisiteNotMetError(EnrollmentError):
    """
    Raised when required prerequisite courses are not completed.

    UML Activity Diagram (Section 7):
        Decision: "Check Prerequisites"
        → If fail: PrerequisiteNotMetError → "Display Error"

    Usage:
        raise PrerequisiteNotMetError(
            "CS101 must be completed before enrolling in CS201"
        )
    """


# ── Course Graph ──────────────────────────────────────────────────────────────

class CircularDependencyError(LMPTSException):
    """
    Raised when adding a prerequisite would create a cycle.

    UML Prerequisite Graph (Section 11):
        Invalid: CS101 → CS201 → CS301 → CS101
        DFS detects the back edge → raises CircularDependencyError

    Usage:
        raise CircularDependencyError(
            "Adding CS101 as prerequisite of CS301 creates a cycle"
        )
    """