from core.course import Course
from core.enums import DifficultyLevel, CourseStatus
from core.exceptions import ValidationError


def main():
    print("=== COURSE VERIFICATION ===")
    print()

    # Create course
    course = Course(
        code="CS101",
        name="Intro to Programming",
        difficulty=DifficultyLevel.BEGINNER,
        duration=30,
        status=CourseStatus.PUBLISHED,
    )
    print(f"Created: {repr(course)}")

    # Verify types (UML: duration=int, prerequisites=set)
    assert isinstance(course.duration, int), "duration must be int"
    assert isinstance(course.prerequisites, set), "prerequisites must be set"
    print(
        f"duration type : {type(course.duration).__name__}  "
        "(expected: int)  PASSED"
    )
    print(
        f"prerequisites : {type(course.prerequisites).__name__} "
        "(expected: set) PASSED"
    )

    # Validate
    course.validate()
    print("validate(): PASSED")

    # Prerequisites
    course.add_prerequisite("CS100")
    print(f"add_prerequisite CS100: {course.get_prerequisites()}")
    assert isinstance(course.get_prerequisites(), set)
    print("get_prerequisites() returns set: PASSED")

    # Idempotent (set property)
    course.add_prerequisite("CS100")
    assert len(course.prerequisites) == 1
    print("add same prerequisite twice (set idempotent): PASSED")

    # has_prerequisite
    assert course.has_prerequisite("CS100") is True
    assert course.has_prerequisite("CS999") is False
    print("has_prerequisite(): PASSED")

    # remove_prerequisite
    course.remove_prerequisite("CS100")
    assert not course.has_prerequisite("CS100")
    print("remove_prerequisite(): PASSED")

    # remove nonexistent (discard - no error)
    course.remove_prerequisite("CS999")
    print("remove nonexistent (safe): PASSED")

    # Self-reference prevention
    try:
        course.add_prerequisite("CS101")
        print("FAILED - should have raised")
    except ValidationError:
        print("Self-prerequisite raises ValidationError: PASSED")

    # Validation failures
    try:
        bad = Course("", "Test", DifficultyLevel.BEGINNER, 10)
        bad.validate()
        print("FAILED - empty code should have raised")
    except ValidationError:
        print("Empty code raises ValidationError: PASSED")

    try:
        bad = Course("CS999", "Test", DifficultyLevel.BEGINNER, 0)
        bad.validate()
        print("FAILED - zero duration should have raised")
    except ValidationError:
        print("Zero duration raises ValidationError: PASSED")

    # to_dict and from_dict
    d = course.to_dict()
    print(f"to_dict(): {d}")
    assert isinstance(d["prerequisites"], list)
    print("to_dict() prerequisites is list: PASSED")

    # Optional: test from_dict if implemented
    if hasattr(Course, "from_dict"):
        restored = Course.from_dict(d)
        print(f"from_dict(): {repr(restored)}")
        print("from_dict(): PASSED")

    # Hashable (needed for sets)
    course_set = {course}
    assert course in course_set
    print("Course is hashable (usable in set): PASSED")

    print()
    print("COURSE OK")


if __name__ == "__main__":
    main()