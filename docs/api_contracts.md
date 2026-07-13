# LMPTS — API Contracts

This document defines the complete contract for every public method in
the LMPTS service layer. Both the Tkinter desktop app (`gui/`) and the
Flask web app (`webapp/`) call exclusively into this layer — no business
logic lives in either UI.

**Reading this document:**
- **Parameters** — all inputs with types and constraints
- **Returns** — exact shape of every return value
- **Raises** — every exception that can be thrown
- **Side Effects** — database writes, notifications created
- **Example** — concrete usage

---

## Table of Contents

1. [CourseService](#1-courseservice)
2. [EnrollmentService](#2-enrollmentservice)
3. [ProgressService](#3-progressservice)
4. [AnalyticsService](#4-analyticsservice)
5. [LearningPathService](#5-learningpathservice)
6. [RecommendationService](#6-recommendationservice)
7. [PriorLearningService](#7-priorlearningservice)
8. [AccountService](#8-accountservice)
9. [ProfileService](#9-profileservice)
10. [AuthService](#10-authservice)
11. [Shared Data Shapes](#11-shared-data-shapes)
12. [Exception Reference](#12-exception-reference)

---

## 1. CourseService

**File:** `services/course_service.py`

Manages course lifecycle, prerequisite graph edges, and study ordering.
Every prerequisite mutation goes through cycle detection before being
written to the database.

---

### `create_course(course)`

Creates a new course and registers it in the prerequisite graph.

| | |
|---|---|
| **Parameters** | `course: Course` — must pass `Course.validate()` |
| **Returns** | `Course` — the saved course object |
| **Raises** | `ValidationError` if course fails validation |
| | `DuplicateCourseError` if course code already exists |
| **Side Effects** | Inserts row into `courses` table; adds node to `CourseGraph` |

**Constraints:**
- `code` — non-empty string, unique across all courses
- `name` — non-empty string
- `duration` — integer > 0
- `difficulty` — must be a valid `DifficultyLevel` enum value
- `status` — defaults to `CourseStatus.DRAFT` on creation

**Example:**
```python
course = Course(
    code="CS101",
    name="Intro to Computer Science",
    description="Foundational CS concepts",
    difficulty=DifficultyLevel.BEGINNER,
    duration=40,
)
saved = course_service.create_course(course)
# saved.status == CourseStatus.DRAFT
# saved.code   == "CS101"
```

---

### `update_course(course)`

Updates an existing course's mutable fields.

| | |
|---|---|
| **Parameters** | `course: Course` — code must already exist |
| **Returns** | `Course` — the updated course object |
| **Raises** | `CourseNotFoundError` if course code does not exist |
| | `ValidationError` if updated fields fail validation |
| **Side Effects** | Updates row in `courses` table |

**Constraints:**
- `code` is immutable — cannot be changed via update
- `prerequisites` set is not updated here — use `add_prerequisite` /
  `remove_prerequisite`

---

### `delete_course(code)`

Permanently deletes a course and all related data.

| | |
|---|---|
| **Parameters** | `code: str` — course code to delete |
| **Returns** | `bool` — `True` if deleted |
| **Raises** | `CourseNotFoundError` if code does not exist |
| **Side Effects** | Cascades: deletes prerequisites, enrollments, progress records; removes node + all edges from `CourseGraph` |

> ⚠️ This operation is irreversible. All learner enrollment and
> progress data for this course is permanently deleted.

---

### `get_course(code)`

Fetches a single course by its primary key.

| | |
|---|---|
| **Parameters** | `code: str` |
| **Returns** | `Course` with `prerequisites` set populated |
| **Raises** | `CourseNotFoundError` if code does not exist |

---

### `get_all_courses()`

Fetches all courses regardless of status.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[Course]` — may be empty |
| **Raises** | — |

---

### `get_published_courses()`

Fetches only courses available for enrollment.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[Course]` where `status == PUBLISHED` |
| **Raises** | — |

---

### `publish_course(code)`

Transitions a course from `DRAFT` to `PUBLISHED`.

| | |
|---|---|
| **Parameters** | `code: str` |
| **Returns** | `Course` with updated status |
| **Raises** | `CourseNotFoundError` if code does not exist |
| | `ValidationError` if current status is not `DRAFT` |

**Valid transitions:**
```
DRAFT → PUBLISHED ✅
PUBLISHED → PUBLISHED ❌ ValidationError
ARCHIVED → PUBLISHED ❌ ValidationError
```

---

### `archive_course(code)`

Transitions a course from `PUBLISHED` to `ARCHIVED`.

| | |
|---|---|
| **Parameters** | `code: str` |
| **Returns** | `Course` with updated status |
| **Raises** | `CourseNotFoundError` if code does not exist |
| | `ValidationError` if current status is not `PUBLISHED` |

**Effect:** Archived courses are hidden from enrollment but existing
enrollments and progress records are preserved.

---

### `add_prerequisite(course_code, prereq_code)`

Adds a directed prerequisite edge to the course graph.

| | |
|---|---|
| **Parameters** | `course_code: str` — the dependent course |
| | `prereq_code: str` — the course that must be completed first |
| **Returns** | `bool` — `True` if edge was added |
| **Raises** | `CourseNotFoundError` if either code does not exist |
| | `CircularDependencyError` if adding this edge would create a cycle |
| **Side Effects** | Inserts row into `prerequisites` junction table; updates `CourseGraph` forward + reverse edges atomically |

**Cycle check:** `CycleDetector.would_create_cycle(prereq_code,
course_code)` is called before any write. If it returns `True`,
the operation is rejected entirely — graph and database unchanged.

**Example:**
```python
# CS201 now requires CS101
course_service.add_prerequisite("CS201", "CS101")  # True

# This would close a loop — rejected
course_service.add_prerequisite("CS101", "CS201")
# raises CircularDependencyError
```

---

### `remove_prerequisite(course_code, prereq_code)`

Removes a prerequisite edge from the course graph.

| | |
|---|---|
| **Parameters** | `course_code: str`, `prereq_code: str` |
| **Returns** | `bool` — `True` if removed, `False` if edge did not exist |
| **Raises** | `CourseNotFoundError` if either code does not exist |
| **Side Effects** | Deletes row from `prerequisites` table; updates `CourseGraph` |

---

### `get_study_order()`

Returns all courses in a valid linear study order.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[str]` — course codes in topological order |
| **Raises** | `ValueError` if a cycle exists in the graph (should not happen if `add_prerequisite` is always used) |

**Algorithm:** Kahn's algorithm (BFS-based topological sort).
Alphabetical tie-breaking for determinism.

---

### `get_course_levels()`

Groups courses into parallel study levels.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[list[str]]` — each inner list is one level |
| **Raises** | — |

**Example:**
```python
course_service.get_course_levels()
# [
#   ["CS101", "CS102", "PY101"],   # Level 0 — no prerequisites
#   ["CS201"],                      # Level 1 — needs CS101 + CS102
#   ["CS301", "ML101"],             # Level 2 — needs CS201
# ]
```

---

## 2. EnrollmentService

**File:** `services/enrollment_service.py`

Manages the full enrollment lifecycle. All prerequisite validation
happens here before any database write. Multi-step operations
(enroll + create progress) run inside a single transaction.

---

### `enroll_learner(learner_id, course_code)`

Validates prerequisites and creates an enrollment record.

| | |
|---|---|
| **Parameters** | `learner_id: int` — database ID of the learner |
| | `course_code: str` — course to enroll in |
| **Returns** | `EnrollmentResult` — see shape below |
| **Raises** | `LearnerNotFoundError` if learner does not exist |
| | `CourseNotFoundError` if course does not exist |
| **Side Effects** | On success: inserts into `enrollments` + `course_progress` (atomic transaction) |

**Validation steps (in order):**
1. Course must exist
2. Course status must be `PUBLISHED`
3. No existing enrollment record for this `(learner_id, course_code)`
   pair — regardless of previous status
4. All direct prerequisites must be in `satisfied_credits`:
   `completed ∪ transfer_credits ∪ exemptions ∪ placement_tests`

**EnrollmentResult shape:**
```python
@dataclass
class EnrollmentResult:
    success: bool
    enrollment: Enrollment | None      # populated if success=True
    missing_prerequisites: list[str]   # populated if success=False
    message: str                       # human-readable explanation
```

**Example:**
```python
result = service.enroll_learner(1, "CS201")

if result.success:
    print(result.enrollment.status)    # EnrollmentStatus.ENROLLED
else:
    print(result.missing_prerequisites)  # ["CS101", "CS102"]
    print(result.message)
    # "Missing prerequisites: CS101, CS102"
```

---

### `start_enrollment(learner_id, course_code)`

Transitions an enrollment from `ENROLLED` to `IN_PROGRESS`.

| | |
|---|---|
| **Parameters** | `learner_id: int`, `course_code: str` |
| **Returns** | `Enrollment` with updated status |
| **Raises** | `EnrollmentError` if no enrollment exists |
| | `EnrollmentError` if current status is not `ENROLLED` |
| **Side Effects** | Updates `enrollments.status` |

---

### `complete_enrollment(learner_id, course_code, score)`

Records a score and marks an enrollment as `COMPLETED`.

| | |
|---|---|
| **Parameters** | `learner_id: int`, `course_code: str` |
| | `score: float` — must be in range 0.0–100.0 |
| **Returns** | `Enrollment` with status `COMPLETED` and score set |
| **Raises** | `EnrollmentError` if no enrollment exists |
| | `EnrollmentError` if current status is not `IN_PROGRESS` |
| | `ValidationError` if score is outside 0–100 |
| **Side Effects** | Updates `enrollments.status`, `enrollments.score`, `enrollments.completed_at`; updates `course_progress` to 100% |

---

### `cancel_enrollment(learner_id, course_code)`

Cancels an enrollment directly (admin or learner action).

| | |
|---|---|
| **Parameters** | `learner_id: int`, `course_code: str` |
| **Returns** | `bool` — `True` if cancelled |
| **Raises** | `EnrollmentError` if no enrollment exists |
| | `EnrollmentError` if status is already `COMPLETED` or `CANCELLED` |
| **Side Effects** | Updates `enrollments.status` to `CANCELLED` |

---

### `transfer_credit(learner_id, course_code)`

Admin action: grants a completed enrollment without the learner
actually completing the course in-system.

| | |
|---|---|
| **Parameters** | `learner_id: int`, `course_code: str` |
| **Returns** | `bool` — `True` if credit granted |
| **Raises** | `LearnerNotFoundError` if learner does not exist |
| | `CourseNotFoundError` if course does not exist |
| **Side Effects** | Inserts `COMPLETED` enrollment + 100% progress record (or updates existing); the course now counts as satisfied for prerequisite checks |

---

### `approve_exemption(learner_id, course_code)`

Admin action: grants course exemption (functionally identical to
transfer credit — marks as `COMPLETED`).

| | |
|---|---|
| **Parameters** | `learner_id: int`, `course_code: str` |
| **Returns** | `bool` — `True` if exemption granted |
| **Raises** | `LearnerNotFoundError`, `CourseNotFoundError` |
| **Side Effects** | Same as `transfer_credit` |

---

## 3. ProgressService

**File:** `services/progress_service.py`

Fine-grained progress tracking separate from enrollment status.
`CompletionStatus` is auto-adjusted based on percentage.

---

### `update_progress(learner_id, course_code, percentage)`

Updates the progress percentage and auto-adjusts `CompletionStatus`.

| | |
|---|---|
| **Parameters** | `learner_id: int`, `course_code: str` |
| | `percentage: float` — must be 0.0–100.0 |
| **Returns** | `CourseProgress` with updated fields |
| **Raises** | `ValidationError` if percentage is out of range |
| **Side Effects** | Updates `course_progress` row |

**Auto-adjustment rules:**
```
percentage == 0.0          → CompletionStatus.NOT_STARTED
0.0 < percentage < 100.0   → CompletionStatus.IN_PROGRESS
percentage == 100.0         → CompletionStatus.COMPLETED
```

---

### `mark_failed(learner_id, course_code)`

Sets `CompletionStatus` to `FAILED` regardless of percentage.

| | |
|---|---|
| **Parameters** | `learner_id: int`, `course_code: str` |
| **Returns** | `CourseProgress` with `completion_status = FAILED` |
| **Raises** | `ValidationError` if no progress record exists |
| **Side Effects** | Updates `course_progress.completion_status` |

> `FAILED` is a terminal state — it cannot be reversed by
> `update_progress`. A new enrollment would be required.

---

### `get_progress(learner_id, course_code)`

Fetches the current progress record.

| | |
|---|---|
| **Parameters** | `learner_id: int`, `course_code: str` |
| **Returns** | `CourseProgress` |
| **Raises** | `ValidationError` if no record exists |

---

### `calculate_completion_rate(learner_id)`

Calculates the learner's overall completion rate.

| | |
|---|---|
| **Parameters** | `learner_id: int` |
| **Returns** | `float` — percentage (0.0–100.0) |
| **Raises** | — (returns 0.0 if learner has no enrollments) |

**Formula:** `completed_count / total_enrolled × 100`

---

### `get_overall_summary(learner_id)`

Returns counts by `CompletionStatus` plus the completion rate.

| | |
|---|---|
| **Parameters** | `learner_id: int` |
| **Returns** | `dict` — see shape below |

**Return shape:**
```python
{
    "not_started":   int,
    "in_progress":   int,
    "completed":     int,
    "failed":        int,
    "total":         int,
    "completion_rate": float,   # 0.0–100.0
}
```

---

### `get_learning_path_progress(learner_id, goal_course)`

Calculates how far along a learner is toward a specific goal course.

| | |
|---|---|
| **Parameters** | `learner_id: int`, `goal_course: str` |
| **Returns** | `dict` — see shape below |
| **Raises** | `CourseNotFoundError` if goal course does not exist |

**Return shape:**
```python
{
    "goal":        str,          # goal course code
    "total":       int,          # total prerequisites + goal
    "completed":   int,          # how many are done
    "remaining":   list[str],    # course codes still needed
    "percentage":  float,        # completion percentage toward goal
}
```

---

## 4. AnalyticsService

**File:** `services/analytics_service.py`

All analytics methods are **read-only** — no database writes.
Results are computed fresh on every call (no caching).
All division operations guard against empty databases.

---

### `system_overview()`

Global system statistics.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `dict` |

**Return shape:**
```python
{
    "total_courses":      int,
    "total_learners":     int,
    "total_enrollments":  int,
    "total_completed":    int,
    "completion_rate":    float,   # 0.0–100.0
    "difficulty_distribution": {
        "BEGINNER":      int,
        "INTERMEDIATE":  int,
        "ADVANCED":      int,
    },
}
```

---

### `course_completion_rate(course_code)`

Per-course enrollment statistics.

| | |
|---|---|
| **Parameters** | `course_code: str` |
| **Returns** | `dict` |
| **Raises** | `CourseNotFoundError` if code does not exist |

**Return shape:**
```python
{
    "course_code":       str,
    "enrolled":          int,
    "completed":         int,
    "in_progress":       int,
    "cancelled":         int,
    "completion_rate":   float,   # completed / enrolled × 100
    "dropout_rate":      float,   # cancelled / enrolled × 100
}
```

---

### `most_enrolled_courses(limit)`

Courses ranked by total enrollment count.

| | |
|---|---|
| **Parameters** | `limit: int = 10` |
| **Returns** | `list[dict]` — ordered by enrollment count descending |

**Each dict:**
```python
{
    "course_code":     str,
    "course_name":     str,
    "enrollment_count": int,
}
```

---

### `bottleneck_courses(threshold)`

Courses with a dropout rate above the given threshold.

| | |
|---|---|
| **Parameters** | `threshold: float = 0.5` — 0.0 to 1.0 |
| **Returns** | `list[dict]` — courses exceeding the dropout threshold |

**Each dict:**
```python
{
    "course_code":   str,
    "course_name":   str,
    "enrolled":      int,
    "cancelled":     int,
    "dropout_rate":  float,
}
```

---

### `average_score_by_course()`

Mean score of completed learners per course.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[dict]` — courses with at least one completed enrollment |

**Each dict:**
```python
{
    "course_code":    str,
    "course_name":    str,
    "average_score":  float,
    "completed_count": int,
}
```

---

### `student_performance_report()`

One row per enrollment across the entire system.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[dict]` |

**Each dict:**
```python
{
    "learner_name":   str,
    "course_code":    str,
    "course_name":    str,
    "score":          float | None,   # None if not yet scored
    "grade":          str,            # A/B/C/D/F or "N/A"
    "status":         str,            # EnrollmentStatus value
}
```

**Grade conversion:**
```
≥ 90 → A
≥ 80 → B
≥ 70 → C
≥ 60 → D
 < 60 → F
None  → N/A
```

---

### `score_bucket_distribution()`

Counts scored enrollments bucketed into performance bands.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `dict` |

**Return shape:**
```python
{
    "Excellent": int,   # score ≥ 90
    "Good":      int,   # score ≥ 75
    "Average":   int,   # score ≥ 50
    "Poor":      int,   # score < 50
}
```

---

### `performance_trend(months)`

Average score per calendar month for the last N months.

| | |
|---|---|
| **Parameters** | `months: int = 6` |
| **Returns** | `list[dict]` — ordered oldest to newest |

**Each dict:**
```python
{
    "month":         str,           # e.g. "Jan 2026"
    "average_score": float | None,  # None = no completions that month
}
```

> `None` (not `0.0`) is used for months with no data so the caller
> can render a genuine gap in a line chart rather than a misleading zero.

---

### `course_completion_breakdown()`

System-wide progress status counts from `course_progress` table.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `dict` |

**Return shape:**
```python
{
    "completed":    int,
    "in_progress":  int,
    "not_started":  int,   # includes FAILED
    "total":        int,
    "completion_pct": float,
}
```

---

### `course_completion_by_course()`

Per-course progress counts shaped for Chart.js stacked bar chart.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `dict` |

**Return shape:**
```python
{
    "labels":       list[str],   # course codes
    "completed":    list[int],
    "in_progress":  list[int],
    "not_started":  list[int],
}
```

---

### `enrollment_monthly_trend(months)`

Enrollment count per calendar month for the last N months.

| | |
|---|---|
| **Parameters** | `months: int = 6` |
| **Returns** | `list[dict]` — ordered oldest to newest |

**Each dict:**
```python
{
    "month": str,   # e.g. "Feb 2026"
    "count": int,   # 0 if no enrollments that month
}
```

---

### `enrollment_summary_metrics()`

Summary metrics for the enrollment analytics stat cards.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `dict` |

**Return shape:**
```python
{
    "total":       int,     # all-time enrollment count
    "this_week":   int,     # enrolled in the last 7 days
    "this_month":  int,     # enrolled in the current calendar month
    "growth_pct":  float,   # month-over-month growth %
}
```

**Growth % edge cases:**
```
last_month == 0 and this_month > 0  →  100.0
last_month == 0 and this_month == 0 →  0.0
otherwise                            →  (this - last) / last × 100
```

---

### `instructor_analytics(instructors, instructor_courses)`

Aggregated per-instructor statistics.

| | |
|---|---|
| **Parameters** | `instructors: list[User]` — all INSTRUCTOR-role users |
| | `instructor_courses: dict[int, set[str]]` — map of instructor_id → set of course codes they submitted |
| **Returns** | `list[dict]` |

**Each dict:**
```python
{
    "instructor_name":   str,
    "courses_created":   int,
    "students_assigned": int,   # distinct learners across all courses
    "completion_rate":   float,
    "average_rating":    str,   # always "N/A" — no ratings in schema
}
```

> `average_rating` is always `"N/A"`. There is no ratings table in
> the database schema. This is an honest "not collected" indicator —
> not a fake or proxy value.

---

### `learner_activity_report()`

All learners ranked by completion rate.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[dict]` — ordered by completion_rate descending |

**Each dict:**
```python
{
    "learner_id":       int,
    "learner_name":     str,
    "enrolled":         int,
    "completed":        int,
    "in_progress":      int,
    "completion_rate":  float,
    "average_score":    float | None,
}
```

---

### `prerequisite_chain_length()`

Number of transitive prerequisites per course.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[dict]` — ordered by chain_length descending |

**Each dict:**
```python
{
    "course_code":   str,
    "course_name":   str,
    "chain_length":  int,   # 0 = no prerequisites
}
```

---

## 5. LearningPathService

**File:** `services/learning_path_service.py`

Generates personalized learning paths using the graph algorithm engine.

---

### `get_path_to_course(start_code, end_code)`

BFS shortest path between two courses.

| | |
|---|---|
| **Parameters** | `start_code: str`, `end_code: str` |
| **Returns** | `list[str]` — ordered course codes, or `None` if unreachable |
| **Raises** | `CourseNotFoundError` if either code does not exist |

**Example:**
```python
service.get_path_to_course("CS101", "CS301")
# ["CS101", "CS201", "CS301"]

service.get_path_to_course("PY101", "CS301")
# None  (no path — PY101 is not a prerequisite of CS301)
```

---

### `get_learner_roadmap(learner_id, goal_code)`

Personalized roadmap showing completed, in-progress, and remaining
courses on the path to a goal.

| | |
|---|---|
| **Parameters** | `learner_id: int`, `goal_code: str` |
| **Returns** | `dict` |
| **Raises** | `LearnerNotFoundError`, `CourseNotFoundError` |

**Return shape:**
```python
{
    "goal":          str,
    "all_required":  list[str],    # all prereqs + goal, in order
    "completed":     list[str],    # already done
    "in_progress":   list[str],    # currently enrolled
    "remaining":     list[str],    # not yet started
    "percentage":    float,        # completion toward goal
    "next_step":     str | None,   # immediate next course to take
}
```

---

### `get_available_next_courses(learner_id)`

Courses the learner can enroll in right now.

| | |
|---|---|
| **Parameters** | `learner_id: int` |
| **Returns** | `list[str]` — published course codes with all prereqs satisfied |
| **Raises** | `LearnerNotFoundError` |

---

### `get_full_curriculum_order()`

All courses in a single valid study order.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[str]` — full topological order |
| **Raises** | `ValueError` if graph contains a cycle |

---

### `get_curriculum_levels()`

Courses grouped into parallel study levels.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[list[str]]` |

---

### `get_prerequisites_for(course_code)`

Ordered list of all prerequisites for a course.

| | |
|---|---|
| **Parameters** | `course_code: str` |
| **Returns** | `list[str]` — in valid study order |
| **Raises** | `CourseNotFoundError` |

---

## 6. RecommendationService

**File:** `services/recommendation_service.py`

Bridges the recommendation algorithm engine with live database data.

---

### `get_recommendations(learner_id, difficulty, limit, goals)`

Returns scored course recommendations for a learner.

| | |
|---|---|
| **Parameters** | `learner_id: int` |
| | `difficulty: DifficultyLevel | None` — filter by difficulty (None = no filter) |
| | `limit: int = 10` — max recommendations to return |
| | `goals: list[str] = []` — target course codes to bias toward |
| **Returns** | `list[dict]` — ordered by score descending |
| **Raises** | `LearnerNotFoundError` |

**Each dict:**
```python
{
    "course_code":  str,
    "course_name":  str,
    "score":        float,       # 0–100
    "difficulty":   str,
    "duration":     int,
    "reasons":      list[str],   # human-readable justifications
    "remaining":    list[str],   # courses unlocked by completing this
}
```

**Scoring formula:**
```
score = (
    prerequisite_score  × 0.40   +  # all prereqs met = 100
    difficulty_match    × 0.30   +  # matches preference = 100
    path_length_score   × 0.20   +  # shorter remaining = higher
    duration_score      × 0.10      # shorter course = higher
)
```

---

### `get_learning_roadmap(learner_id, goals)`

Multi-goal roadmap across several target courses.

| | |
|---|---|
| **Parameters** | `learner_id: int`, `goals: list[str]` |
| **Returns** | `dict[str, dict]` — maps goal code → roadmap dict (same shape as `get_learner_roadmap`) |
| **Raises** | `LearnerNotFoundError` |

---

## 7. PriorLearningService

**File:** `services/prior_learning_service.py`

Orchestrates the three-stage prior learning recognition workflow:
Learner submits → Instructor reviews → Admin decides.

---

### `submit_request(learner_id, course_code, pathway, evidence, platform, score)`

Learner submits a prior learning recognition request.

| | |
|---|---|
| **Parameters** | `learner_id: int` |
| | `course_code: str` |
| | `pathway: str` — `"TRANSFER"`, `"ASSESSMENT"`, or `"EXEMPTION"` |
| | `evidence: str` — minimum 30 characters |
| | `platform: str | None` — external platform name (optional) |
| | `score: float | None` — external score (optional) |
| **Returns** | `PriorLearningRequest` with status `PENDING` |
| **Raises** | `LearnerNotFoundError`, `CourseNotFoundError` |
| | `ValidationError` if evidence is fewer than 30 characters |
| | `ValidationError` if pathway is not a valid value |
| **Side Effects** | Inserts into `prior_learning_requests`; notifies all instructors |

---

### `instructor_review(request_id, recommendation, note, instructor_id)`

Instructor provides their recommendation on a PLR request.

| | |
|---|---|
| **Parameters** | `request_id: int` |
| | `recommendation: str` — `"APPROVE"`, `"REJECT"`, or `"INFO_REQUESTED"` |
| | `note: str` — review notes for admin |
| | `instructor_id: int` |
| **Returns** | `PriorLearningRequest` with status `INSTRUCTOR_REVIEWED` |
| **Raises** | `ValidationError` if request not found or not in `PENDING` status |
| **Side Effects** | Updates request; notifies all admins |

---

### `admin_decision(request_id, decision, note, admin_id)`

Admin makes the final binding decision on a PLR request.

| | |
|---|---|
| **Parameters** | `request_id: int` |
| | `decision: str` — `"APPROVED"` or `"REJECTED"` |
| | `note: str` — admin's decision note |
| | `admin_id: int` |
| **Returns** | `PriorLearningRequest` with final status |
| **Raises** | `ValidationError` if request not in `INSTRUCTOR_REVIEWED` status |
| **Side Effects** | Updates request status; if `APPROVED` calls `transfer_credit()` automatically; notifies learner |

---

### `get_learner_requests(learner_id)`

All PLR requests submitted by a learner.

| | |
|---|---|
| **Parameters** | `learner_id: int` |
| **Returns** | `list[PriorLearningRequest]` — ordered newest first |

---

### `get_pending_instructor_review()`

All requests awaiting instructor review.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[PriorLearningRequest]` where status is `PENDING` |

---

### `get_pending_admin_decision()`

All requests awaiting admin final decision.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[PriorLearningRequest]` where status is `INSTRUCTOR_REVIEWED` |

---

## 8. AccountService

**File:** `services/account_service.py`

Manages the learner self-registration approval workflow and
account lifecycle (deactivation, reactivation).

---

### `get_pending_registrations()`

All accounts awaiting admin approval.

| | |
|---|---|
| **Parameters** | None |
| **Returns** | `list[User]` where `account_status == PENDING` |

---

### `approve_registration(user_id, admin_id, note)`

Activates a pending learner account.

| | |
|---|---|
| **Parameters** | `user_id: int`, `admin_id: int`, `note: str` |
| **Returns** | `bool` — `True` if approved |
| **Raises** | `ValidationError` if user not found or not in PENDING status |
| **Side Effects** | Sets `is_active = True`, `account_status = ACTIVE`; creates `Learner` profile record; notifies learner (SUCCESS) |

---

### `reject_registration(user_id, admin_id, reason)`

Rejects a pending learner registration.

| | |
|---|---|
| **Parameters** | `user_id: int`, `admin_id: int`, `reason: str` — mandatory |
| **Returns** | `bool` — `True` if rejected |
| **Raises** | `ValidationError` if reason is empty |
| **Side Effects** | Sets `account_status = REJECTED`, stores `rejection_reason`; notifies learner (WARNING) |

---

### `request_more_information(user_id, admin_id, message)`

Keeps account PENDING and records an information request.

| | |
|---|---|
| **Parameters** | `user_id: int`, `admin_id: int`, `message: str` |
| **Returns** | `bool` — `True` if recorded |
| **Side Effects** | Account stays PENDING; message stored as notification |

---

### `deactivate_user(user_id, admin_id, reason)`

Suspends an active account.

| | |
|---|---|
| **Parameters** | `user_id: int`, `admin_id: int`, `reason: str` |
| **Returns** | `bool` — `True` if deactivated |
| **Side Effects** | Sets `is_active = False`, `account_status = INACTIVE`; notifies user (WARNING) |

---

### `reactivate_user(user_id, admin_id)`

Restores a suspended or rejected account.

| | |
|---|---|
| **Parameters** | `user_id: int`, `admin_id: int` |
| **Returns** | `bool` — `True` if reactivated |
| **Side Effects** | Sets `is_active = True`, `account_status = ACTIVE`; notifies user (SUCCESS) |

---

## 9. ProfileService

**File:** `services/profile_service.py`

Profile management for all roles. Changes to a learner's name or
email automatically sync to the linked `Learner` record.

---

### `get_profile(user_id)`

Fetches the full user profile.

| | |
|---|---|
| **Parameters** | `user_id: int` |
| **Returns** | `User` with all profile fields populated |
| **Raises** | `ValidationError` if user not found |

---

### `update_personal_info(user_id, full_name, email, bio, preferred_difficulty)`

Saves updated profile information.

| | |
|---|---|
| **Parameters** | `user_id: int` |
| | `full_name: str` — non-empty |
| | `email: str` — valid email format |
| | `bio: str` — maximum 500 characters |
| | `preferred_difficulty: DifficultyLevel | None` — learners only |
| **Returns** | `User` — updated profile |
| **Raises** | `ValidationError` if email format invalid |
| | `ValidationError` if bio exceeds 500 characters |
| **Side Effects** | Updates `users` table; if learner: syncs `learners.name` and `learners.email`; if email changed: notifies user (INFO) |

---

### `change_password(user_id, old_password, new_password)`

Changes a user's password after verifying the current one.

| | |
|---|---|
| **Parameters** | `user_id: int` |
| | `old_password: str` — must match current bcrypt hash |
| | `new_password: str` — must meet complexity requirements |
| **Returns** | `bool` — `True` if changed |
| **Raises** | `AuthenticationError` if old_password is incorrect |
| | `ValidationError` if new password fails complexity check |
| **Side Effects** | Updates `users.password_hash`; creates notification (SUCCESS); caller should force logout after this call |

**Complexity requirements:**
```
✓ Minimum 8 characters
✓ At least one uppercase letter
✓ At least one digit
✓ Must differ from current password
```

---

### `calculate_password_strength(password)`

Scores a password's strength for live feedback on forms.

| | |
|---|---|
| **Parameters** | `password: str` |
| **Returns** | `dict` — see shape below |
| **Raises** | — (never raises; empty string returns score 0) |

**Return shape:**
```python
{
    "score":  int,        # 0–100
    "label":  str,        # "Weak" / "Fair" / "Good" / "Strong"
    "color":  str,        # "red" / "orange" / "blue" / "green"
    "issues": list[str],  # unmet mandatory requirements
}
```

**Score calculation:**
```
Length ≥  8  → +25     Has uppercase → +15
Length ≥ 12  → +15     Has lowercase → +10
Length ≥ 16  → +10     Has digit     → +15
                        Has special   → +10

Labels:
  0  – 29  → Weak   (red)
  30 – 59  → Fair   (orange)
  60 – 79  → Good   (blue)
  80 – 100 → Strong (green)
```

---

## 10. AuthService

**File:** `auth/auth_service.py`

Handles credential verification, account creation, and password
changes. Used directly by both UIs.

---

### `login(username, password)`

Verifies credentials and returns the authenticated user.

| | |
|---|---|
| **Parameters** | `username: str`, `password: str` |
| **Returns** | `User` — the authenticated user object |
| **Raises** | `AuthenticationError` with specific message per failure mode |

**Rejection messages by account state:**
```
User not found              → "Invalid username or password"
Password wrong              → "Invalid username or password"
account_status == PENDING   → "Your account is pending admin approval. Please wait..."
account_status == REJECTED  → "Your registration was rejected. Reason: {reason}"
account_status == INACTIVE  → "Your account has been deactivated. Contact admin."
```

> Same message for "not found" and "wrong password" prevents
> username enumeration attacks.

---

### `register(username, password, role, full_name, email)`

Admin-created account — activated immediately.

| | |
|---|---|
| **Parameters** | `username: str` — 3–20 chars, alphanumeric + underscore |
| | `password: str` — minimum 8 characters |
| | `role: UserRole` — any role |
| | `full_name: str`, `email: str` |
| **Returns** | `User` with `account_status = ACTIVE`, `is_active = True` |
| **Raises** | `ValidationError` if username taken or constraints fail |
| **Side Effects** | Inserts into `users` table |

---

### `register_learner(username, password, full_name, email)`

Self-registration — account starts as PENDING.

| | |
|---|---|
| **Parameters** | `username: str`, `password: str`, `full_name: str`, `email: str` |
| **Returns** | `User` with `account_status = PENDING`, `is_active = False` |
| **Raises** | `ValidationError` if username taken or constraints fail |
| **Side Effects** | Inserts into `users` table; notifies all admins |

---

## 11. Shared Data Shapes

### Course

```python
@dataclass
class Course:
    code:          str                  # Primary key, e.g. "CS101"
    name:          str
    description:   str
    difficulty:    DifficultyLevel      # BEGINNER / INTERMEDIATE / ADVANCED
    duration:      int                  # Hours, must be > 0
    status:        CourseStatus         # DRAFT / PUBLISHED / ARCHIVED
    prerequisites: set[str]             # Set of course codes
```

### Enrollment

```python
@dataclass
class Enrollment:
    id:           int
    learner_id:   int
    course_code:  str
    status:       EnrollmentStatus      # ENROLLED / IN_PROGRESS / COMPLETED / CANCELLED
    score:        float | None          # 0–100, set on completion
    enrolled_at:  datetime
    completed_at: datetime | None
```

### CourseProgress

```python
@dataclass
class CourseProgress:
    id:                int
    learner_id:        int
    course_code:       str
    percentage:        float            # 0.0–100.0
    completion_status: CompletionStatus # NOT_STARTED / IN_PROGRESS / COMPLETED / FAILED
    updated_at:        datetime
```

### LearnerCredits

```python
@dataclass
class LearnerCredits:
    completed:        set[str]   # Normally completed courses
    transfer_credits: set[str]   # Approved transfer credits
    exemptions:       set[str]   # Admin-granted exemptions
    placement_tests:  set[str]   # Via placement exam

    @property
    def all_satisfied(self) -> set[str]:
        return (self.completed | self.transfer_credits
                | self.exemptions | self.placement_tests)
```

### PriorLearningRequest

```python
@dataclass
class PriorLearningRequest:
    id:                          int
    learner_id:                  int
    course_code:                 str
    pathway:                     str    # TRANSFER / ASSESSMENT / EXEMPTION
    evidence_description:        str
    external_platform:           str | None
    external_score:              float | None
    status:                      str    # PENDING / INSTRUCTOR_REVIEWED / APPROVED / REJECTED
    instructor_recommendation:   str | None
    instructor_note:             str | None
    instructor_id:               int | None
    admin_note:                  str | None
    admin_id:                    int | None
    submitted_at:                datetime
    reviewed_by_instructor_at:   datetime | None
    decided_by_admin_at:         datetime | None
```

---

## 12. Exception Reference

All exceptions inherit from `LMPTSException`.

```
LMPTSException
    ├── ValidationError
    │       Raised when: input fails business rules, status transitions
    │       are invalid, constraints not met
    │
    ├── AuthenticationError
    │       Raised when: login fails, old password incorrect
    │
    ├── CourseNotFoundError
    │       Raised when: course code does not exist in database
    │
    ├── LearnerNotFoundError
    │       Raised when: learner ID does not exist in database
    │
    ├── EnrollmentError
    │       Raised when: enrollment state machine transition is invalid
    │       ├── DuplicateEnrollmentError
    │       │       Raised when: learner already has any enrollment record
    │       │       for the course (regardless of status)
    │       └── PrerequisiteNotMetError
    │               Raised when: hard prerequisite block (not returned
    │               as EnrollmentResult — only raised if validator is
    │               called directly)
    │
    └── CircularDependencyError
            Raised when: adding a prerequisite edge would create a cycle
            Contains: the cycle path as a list of course codes
```

**Catching exceptions:**
```python
# Broad catch — any LMPTS error
try:
    service.add_prerequisite("CS101", "CS301")
except LMPTSException as e:
    print(f"Operation failed: {e}")

# Precise catch
try:
    service.add_prerequisite("CS101", "CS301")
except CircularDependencyError as e:
    print(f"Cycle detected: {e.cycle_path}")
except CourseNotFoundError as e:
    print(f"Course not found: {e}")
```