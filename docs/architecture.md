# LMPTS — System Architecture

This document is the definitive reference for how LMPTS is structured
internally — the layers, the data flows, the algorithm engine, the
dual-UI strategy, and every design decision that shapes the codebase.

---

## Table of Contents

1. [High-Level Overview](#1-high-level-overview)
2. [Layered Architecture](#2-layered-architecture)
3. [Layer Rules](#3-layer-rules)
4. [Core Layer](#4-core-layer)
5. [Authentication Layer](#5-authentication-layer)
6. [Algorithm Engine](#6-algorithm-engine)
7. [Repository Layer](#7-repository-layer)
8. [Service Layer](#8-service-layer)
9. [Desktop GUI Layer](#9-desktop-gui-layer)
10. [Web Application Layer](#10-web-application-layer)
11. [Dual-UI Strategy](#11-dual-ui-strategy)
12. [Design Patterns](#12-design-patterns)
13. [Data Flow Walkthroughs](#13-data-flow-walkthroughs)
14. [Error Handling Strategy](#14-error-handling-strategy)
15. [Security Design](#15-security-design)
16. [Testing Architecture](#16-testing-architecture)
17. [Key Design Decisions](#17-key-design-decisions)

---

## 1. High-Level Overview

LMPTS is built on a **strict layered architecture** where every layer
has a single responsibility and may only communicate downward — never
upward, never sideways across the UI boundary.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                         │
│                                                                    │
│   Desktop UI (Tkinter)              Web UI (Flask + Jinja2)       │
│   gui/app.py                        run_web.py                    │
│   gui/main_window.py                webapp/__init__.py            │
│   gui/admin/   gui/learner/         webapp/admin.py               │
│   gui/instructor/ gui/analyst/      webapp/learner.py             │
│   gui/profile/ gui/widgets/         webapp/analyst.py             │
│                                     webapp/instructor.py          │
│                                     webapp/profile.py             │
└───────────────────────┬─────────────────────────┬────────────────┘
                        │ calls into               │ calls into
                        │ (same objects)           │ (same objects)
┌───────────────────────▼─────────────────────────▼────────────────┐
│                         Service Layer                              │
│                                                                    │
│   CourseService          EnrollmentService                        │
│   ProgressService        AnalyticsService                         │
│   LearningPathService    RecommendationService                    │
│   PriorLearningService   AccountService                           │
│   ProfileService                                                   │
└──────────────────┬──────────────────────────┬────────────────────┘
                   │ uses                      │ uses
┌──────────────────▼──────────┐  ┌────────────▼──────────────────┐
│      Algorithm Engine        │  │       Repository Layer         │
│                              │  │                                │
│  CourseGraph                 │  │  SQLiteUserRepository          │
│  CycleDetector (DFS)         │  │  SQLiteCourseRepository        │
│  PathFinder (BFS)            │  │  SQLiteLearnerRepository       │
│  TopologicalSorter           │  │  SQLiteEnrollmentRepository    │
│  PrerequisiteValidator       │  │  SQLiteProgressRepository      │
│  RecommendationEngine        │  │  SQLitePriorLearningRepository │
└─────────────────────────────┘  │  SQLiteNotificationRepository  │
                                  │  SQLiteCancellationRepository  │
                                  └────────────────┬──────────────┘
                                                   │ reads/writes
┌──────────────────────────────────────────────────▼──────────────┐
│                    Core Models + Auth                             │
│                                                                    │
│  User          Course         Learner        Enrollment           │
│  CourseProgress UserProfile   CancellationRequest                 │
│  PriorLearningRequest         Notification   Enums                │
│  Exceptions                                                        │
│                                                                    │
│  PasswordManager    AuthService    SessionManager                  │
└──────────────────────────────────────────────────┬──────────────┘
                                                   │ persists to
┌──────────────────────────────────────────────────▼──────────────┐
│                       SQLite Database                             │
│                       data/lmpts.db                               │
│                       data/seed_data.sql                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Layered Architecture

Each layer has one job and one job only:

| Layer | Folder | Responsibility |
|-------|--------|---------------|
| **Core** | `core/` | Domain models, enumerations, exceptions — no framework dependency |
| **Auth** | `auth/` | Password hashing, login logic, session tracking |
| **Algorithms** | `algorithms/` | Graph operations, cycle detection, path finding, recommendations |
| **Repository** | `repository/` | SQLite read/write — one repository per aggregate |
| **Services** | `services/` | Business logic and use case orchestration |
| **Desktop UI** | `gui/` | Tkinter widgets, windows, dialogs — role-based screens |
| **Web UI** | `webapp/` | Flask blueprints, Jinja2 templates, static assets |

### What Each Layer Knows About

```
core/        knows about:  Python standard library only
auth/        knows about:  core/
algorithms/  knows about:  core/
repository/  knows about:  core/
services/    knows about:  core/, auth/, algorithms/, repository/
gui/         knows about:  core/, auth/, algorithms/, repository/, services/
webapp/      knows about:  core/, auth/, algorithms/, repository/, services/
```

---

## 3. Layer Rules

These rules are absolute. Violating them breaks the architecture.

### Rule 1 — No Upward Imports

```
# ✅ Service imports from repository
# services/enrollment_service.py
from repository.enrollment_repo import SQLiteEnrollmentRepository

# ❌ Repository imports from service — NEVER
# repository/enrollment_repo.py
from services.enrollment_service import EnrollmentService  # WRONG
```

### Rule 2 — No Cross-UI Imports

```
# ❌ webapp imports from gui — NEVER
# webapp/learner.py
from gui.learner.enrollments import EnrollmentScreen  # WRONG

# ❌ gui imports from webapp — NEVER
# gui/learner/enrollments.py
from webapp.learner import enroll_route  # WRONG
```

### Rule 3 — No Business Logic in UI Layers

```python
# ❌ Wrong — prerequisite check inside a Flask route
@learner_bp.route("/enroll/<code>", methods=["POST"])
def enroll(code):
    learner = get_current_learner()
    course = course_repo.get_course(code)
    if course.prerequisites - learner.completed_courses:
        flash("Missing prerequisites")
        return redirect(...)
    # ... insert enrollment ...

# ✅ Correct — delegate to service
@learner_bp.route("/enroll/<code>", methods=["POST"])
def enroll(code):
    result = enrollment_service.enroll_learner(
        session["learner_id"], code
    )
    if not result.success:
        flash(result.message)
    return redirect(...)
```

### Rule 4 — No Direct Database Access in Services

```python
# ❌ Wrong — raw SQL inside a service
class EnrollmentService:
    def enroll_learner(self, learner_id, code):
        conn = sqlite3.connect("data/lmpts.db")
        conn.execute("INSERT INTO enrollments ...")  # WRONG

# ✅ Correct — use the injected repository
class EnrollmentService:
    def __init__(self, enrollment_repo, ...):
        self._enrollment_repo = enrollment_repo

    def enroll_learner(self, learner_id, code):
        self._enrollment_repo.create_enrollment(...)
```

### Rule 5 — Core Has No Dependencies

```python
# ❌ Wrong — core model imports from service
# core/course.py
from services.course_service import CourseService  # WRONG

# ✅ Correct — core only uses standard library
# core/course.py
from dataclasses import dataclass, field
from core.enums import DifficultyLevel, CourseStatus
```

---

## 4. Core Layer

**Folder:** `core/`

The foundation of the entire system. Contains all domain models,
enumerations, and exceptions. Has zero dependency on any other
LMPTS layer or external framework.

### Models

| File | Class | Purpose |
|------|-------|---------|
| `user.py` | `User` | System account with auth + profile fields |
| `user_profile.py` | `UserProfile` | Extended profile data |
| `course.py` | `Course` | Course with prerequisite set |
| `learner.py` | `Learner` | Student with derived course sets |
| `enrollment.py` | `Enrollment` | One learner ↔ one course with state machine |
| `course_progress.py` | `CourseProgress` | Fine-grained 0–100% progress |
| `cancellation_request.py` | `CancellationRequest` | Enrollment cancellation workflow |
| `prior_learning_request.py` | `PriorLearningRequest` | Transfer credit workflow |
| `notification.py` | `Notification` | In-app message |

### Enumerations (`core/enums.py`)

```python
class UserRole(Enum):
    ADMIN      = "ADMIN"
    LEARNER    = "LEARNER"
    INSTRUCTOR = "INSTRUCTOR"
    ANALYST    = "ANALYST"

class CourseStatus(Enum):
    DRAFT     = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED  = "ARCHIVED"

class EnrollmentStatus(Enum):
    ENROLLED    = "ENROLLED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    CANCELLED   = "CANCELLED"

class DifficultyLevel(Enum):
    BEGINNER     = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED     = "ADVANCED"

class CompletionStatus(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    FAILED      = "FAILED"

class AccountStatus(Enum):
    ACTIVE   = "ACTIVE"
    PENDING  = "PENDING"
    REJECTED = "REJECTED"
    INACTIVE = "INACTIVE"
```

**Why enums?** Prevents magic strings. `UserRole.ADMIN` is safer
than the string `"admin"` — a typo in an enum causes an `AttributeError`
immediately; a typo in a string silently passes comparisons.

### Exception Hierarchy (`core/exceptions.py`)

```
Exception
    └── LMPTSException                ← base for all LMPTS errors
            ├── ValidationError       ← input / business rule failure
            ├── AuthenticationError   ← login / password failure
            ├── CourseNotFoundError   ← course code not in database
            ├── LearnerNotFoundError  ← learner ID not in database
            ├── EnrollmentError       ← enrollment state violation
            │       ├── DuplicateEnrollmentError
            │       └── PrerequisiteNotMetError
            └── CircularDependencyError ← would create cycle in graph
```

**Usage pattern:**
```python
# Catch broadly
try:
    service.add_prerequisite("CS101", "CS301")
except LMPTSException as e:
    show_error(str(e))

# Catch precisely
try:
    service.add_prerequisite("CS101", "CS301")
except CircularDependencyError as e:
    show_error(f"Cycle detected: {e.cycle_path}")
except CourseNotFoundError:
    show_error("Course does not exist")
```

### Course Model Detail

```python
@dataclass
class Course:
    code:          str
    name:          str
    description:   str
    difficulty:    DifficultyLevel
    duration:      int               # hours, must be > 0
    status:        CourseStatus      # DRAFT by default
    prerequisites: set[str]          # set — not list, prevents duplicates

    def add_prerequisite(self, code: str) -> None:
        """Idempotent — adding twice has no effect (set semantics)."""
        self.prerequisites.add(code)

    def remove_prerequisite(self, code: str) -> None:
        """Safe even if code not present (set.discard)."""
        self.prerequisites.discard(code)

    def get_prerequisites(self) -> set[str]:
        """Returns a copy — external code cannot mutate internal state."""
        return self.prerequisites.copy()
```

**Why `set` for prerequisites?**
- Guarantees uniqueness at the data-structure level
- O(1) membership test (`"CS101" in course.prerequisites`)
- Natural match for set operations in `PrerequisiteValidator`

### Enrollment State Machine

```
              ┌──────────────────┐
   [new] ────►│    ENROLLED      │
              └────────┬─────────┘
                       │ start()
              ┌────────▼─────────┐
              │   IN_PROGRESS    │
              └────┬─────────┬───┘
                   │         │
           complete(score)  cancel()
                   │         │
         ┌─────────▼───┐  ┌──▼──────────┐
         │  COMPLETED  │  │  CANCELLED  │
         └─────────────┘  └─────────────┘
              [terminal]       [terminal]

Also valid:
ENROLLED ──► CANCELLED (direct cancel before starting)
```

---

## 5. Authentication Layer

**Folder:** `auth/`

### PasswordManager (`auth/password_manager.py`)

Class-based bcrypt wrapper. Every hash has a unique salt — two calls
to `hash_password("same")` produce different hashes.

```python
class PasswordManager:

    def hash_password(self, plain: str) -> str:
        """Hash using bcrypt with unique salt per call."""
        return bcrypt.hashpw(
            plain.encode(), bcrypt.gensalt()
        ).decode()

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Constant-time comparison — prevents timing attacks."""
        if not plain or not hashed:
            return False
        return bcrypt.checkpw(plain.encode(), hashed.encode())
```

**Security properties:**
- Unique salt per hash — rainbow table attacks defeated
- Constant-time comparison — timing attacks defeated
- Empty input guard — never crashes on empty strings

### SessionManager (`auth/session_manager.py`)

Singleton pattern — exactly one instance exists per process.
Used **only** by the desktop app.

```python
class SessionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._user = None
        return cls._instance

    def login(self, user: User) -> None:
        self._user = user

    def logout(self) -> None:
        self._user = None

    def current_user(self) -> User | None:
        return self._user

    def is_authenticated(self) -> bool:
        return self._user is not None

    @classmethod
    def reset(cls) -> None:
        """Test helper — clears singleton state between tests."""
        if cls._instance:
            cls._instance._user = None
```

**Why Singleton for desktop?** One desktop process = one logged-in
user at a time. The Singleton enforces this invariant application-wide.

**Why NOT Singleton for web?** Multiple concurrent HTTP requests
would overwrite each other's login state. The web app uses Flask's
signed cookie session instead — each request carries its own
`session['user_id']`.

### AuthService (`auth/auth_service.py`)

```
Login flow:
    1. Find user by username
       ├── Not found → AuthenticationError("Invalid username or password")
    2. Check account_status
       ├── PENDING  → AuthenticationError("Your account is pending...")
       ├── REJECTED → AuthenticationError("Rejected. Reason: ...")
       └── INACTIVE → AuthenticationError("Account deactivated...")
    3. Verify password (bcrypt)
       └── Wrong → AuthenticationError("Invalid username or password")
    4. Return User object
```

Same error message for "not found" and "wrong password" prevents
username enumeration: an attacker cannot determine whether a username
exists by observing the error message.

---

## 6. Algorithm Engine

**Folder:** `algorithms/`

Pure computation — no database access, no service imports.
All algorithms operate on the in-memory `CourseGraph`.

### CourseGraph (`algorithms/graph.py`)

Directed graph with **two internal adjacency dictionaries** maintained
in sync on every mutation:

```python
class CourseGraph:

    def __init__(self):
        self.graph         = defaultdict(set)  # forward:  prereq → dependents
        self.reverse_graph = defaultdict(set)  # backward: course → its prereqs

    def add_edge(self, prereq: str, dependent: str) -> None:
        """Add edge and update both directions atomically."""
        self.graph[prereq].add(dependent)
        self.reverse_graph[dependent].add(prereq)

    def remove_edge(self, prereq: str, dependent: str) -> None:
        self.graph[prereq].discard(dependent)
        self.reverse_graph[dependent].discard(prereq)
```

**Why two graphs?**

| Graph | Used By | Query |
|-------|---------|-------|
| Forward (`graph`) | PathFinder, TopologicalSorter | "What does CS101 unlock?" |
| Reverse (`reverse_graph`) | PrerequisiteValidator, CycleDetector | "What does CS301 require?" |

Both are updated atomically on every `add_edge` / `remove_edge` call.
There is never a moment where one is ahead of the other.

**Key graph queries:**

```python
# Direct prerequisites of CS201
graph.get_prerequisites("CS201")
# → {"CS101", "CS102"}

# ALL transitive prerequisites (BFS over reverse_graph)
graph.get_all_prerequisites("CS301")
# → {"CS101", "CS102", "CS201"}

# All courses unlocked by completing CS101
graph.get_all_dependents("CS101")
# → {"CS201", "CS301", "ML101"}
```

---

### CycleDetector (`algorithms/cycle_detection.py`)

DFS with a **recursion stack** (grey/white/black node coloring).

```
Algorithm:
    For each unvisited node:
        Mark GREY (in recursion stack)
        For each neighbor:
            If GREY → back edge found → CYCLE EXISTS
            If WHITE → recurse
        Mark BLACK (fully processed)
```

```python
def would_create_cycle(self, prereq: str, dependent: str) -> bool:
    """
    Checks WITHOUT modifying the real graph.
    Temporarily adds the edge to a copy, runs DFS, discards copy.
    """
    test_graph = copy.deepcopy(self._graph)
    test_graph.add_edge(prereq, dependent)
    return CycleDetector(test_graph)._has_cycle()
```

**Critical guarantee:** `would_create_cycle()` never modifies the
real graph. If it returns `True`, `add_prerequisite()` raises
`CircularDependencyError` and nothing is written to the database.

---

### TopologicalSorter (`algorithms/topological_sort.py`)

**Kahn's Algorithm** (BFS-based, iterative — not recursive, so no
stack overflow on large graphs).

```
Algorithm:
    1. Compute in-degree for every node
    2. Queue all nodes with in-degree = 0
       (alphabetical order for determinism)
    3. While queue not empty:
       a. Dequeue node → append to result
       b. For each dependent: decrement in-degree
       c. If in-degree reaches 0 → enqueue
    4. If result.length < node count → cycle exists
       (some nodes were never reachable from in-degree=0)
```

**Parallel levels:**
```python
def get_levels(self) -> list[list[str]]:
    """
    Groups nodes into levels where all nodes in a level
    can be studied simultaneously (no inter-dependencies).

    Example output:
        [
            ["CS101", "CS102", "PY101"],   # Level 0
            ["CS201"],                      # Level 1
            ["CS301", "ML101"],             # Level 2
        ]
    """
```

---

### PathFinder (`algorithms/path_finder.py`)

**BFS shortest path** — guarantees the fewest-hops path, not
necessarily the easiest.

```
Algorithm:
    Queue = deque([(start, [start])])
    Visited = {start}

    While queue not empty:
        current, path = queue.popleft()
        If current == target: return path
        For each neighbor not in Visited:
            Visited.add(neighbor)
            queue.append((neighbor, path + [neighbor]))

    Return None  ← no path exists
```

**Key methods:**

```python
# Shortest path between two specific courses
finder.find_learning_path("CS101", "CS301")
# → ["CS101", "CS201", "CS301"]

# All prerequisites in valid study order
finder.find_all_prerequisites("CS301")
# → ["CS101", "CS102", "CS201", "CS301"]

# Remaining courses needed (respects completed + transfers)
finder.get_recommended_path(
    target="CS301",
    completed={"CS101"},
    transfers={"CS102"},
    exemptions=set()
)
# → ["CS201", "CS301"]  (CS101 + CS102 already satisfied)
```

---

### PrerequisiteValidator (`algorithms/prerequisite_validator.py`)

The enrollment gate. Determines whether a learner's credits satisfy
a course's requirements.

```python
@dataclass
class LearnerCredits:
    completed:        set[str]   # completed normally
    transfer_credits: set[str]   # approved transfers
    exemptions:       set[str]   # admin exemptions
    placement_tests:  set[str]   # placement exams

    @property
    def all_satisfied(self) -> set[str]:
        return (self.completed | self.transfer_credits
                | self.exemptions | self.placement_tests)

@dataclass
class ValidationResult:
    can_enroll:             bool
    missing_prerequisites:  list[str]
    satisfied_by:           dict[str, str]  # course → credit type
    message:                str

    def __bool__(self) -> bool:
        return self.can_enroll
```

**Validation formula:**
```
required = graph.get_prerequisites(course_code)
satisfied = credits.all_satisfied
missing = required - satisfied

can_enroll = len(missing) == 0
```

---

### RecommendationEngine (`algorithms/recommendation.py`)

Multi-factor scoring. Each unenrolled course gets a score 0–100.

```
score = (
    prerequisite_score  × 0.40
    difficulty_match    × 0.30
    path_length_score   × 0.20
    duration_score      × 0.10
)
```

**Factor details:**

| Factor | Calculation |
|--------|-------------|
| `prerequisite_score` | Ratio of satisfied prereqs: `satisfied / total × 100` |
| `difficulty_match` | `100` if matches preference, `50` if adjacent, `0` if far |
| `path_length_score` | Inverse of remaining path: shorter remaining = higher score |
| `duration_score` | Inverse of duration: shorter course = higher score |

Each recommendation also includes a `reasons` list:
```python
reasons = [
    "All prerequisites are satisfied",
    "Matches your preferred difficulty level",
    "Only 2 courses away from your goal",
]
```

---

## 7. Repository Layer

**Folder:** `repository/`

One repository class per database aggregate. All SQL lives here —
none in services, none in GUI, none in algorithms.

### Database Class (`repository/database.py`)

```python
class Database:
    """
    Core infrastructure:
    - Connection-per-operation pattern
    - Transaction context manager
    - Schema migrations v1–v4
    - WAL journal mode
    - Foreign key enforcement
    """

    @contextmanager
    def transaction(self):
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
```

### Repository Map

| Class | File | Aggregates |
|-------|------|-----------|
| `SQLiteUserRepository` | `user_repo.py` | `users` table |
| `InMemoryUserRepository` | `user_repo.py` | In-memory dict (tests only) |
| `SQLiteCourseRepository` | `course_repo.py` | `courses` + `prerequisites` |
| `SQLiteLearnerRepository` | `learner_repo.py` | `learners` (derives enrolled/completed) |
| `SQLiteEnrollmentRepository` | `enrollment_repo.py` | `enrollments` |
| `SQLiteProgressRepository` | `enrollment_repo.py` | `course_progress` |
| `SQLitePriorLearningRepository` | `prior_learning_repo.py` | `prior_learning_requests` |
| `SQLiteNotificationRepository` | `prior_learning_repo.py` | `notifications` |
| `SQLiteCancellationRepository` | `cancellation_request_repo.py` | `cancellation_requests` |
| `SQLiteCourseSubmissionRepository` | `prior_learning_repo.py` | `course_submissions` |

### Repository Pattern

```python
class SQLiteCourseRepository:
    """
    All SQL for the courses aggregate lives here.
    Services never write SQL — they call these methods.
    """

    def __init__(self, db: Database):
        self._db = db

    def save(self, course: Course) -> Course:
        with self._db.transaction() as conn:
            conn.execute(
                """INSERT INTO courses
                   (code, name, description, difficulty, duration, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (course.code, course.name, course.description,
                 course.difficulty.value, course.duration,
                 course.status.value)
            )
        return course

    def _row_to_course(self, row) -> Course:
        """
        Always deserialize through this method.
        Handles enum conversion from stored strings.
        """
        return Course(
            code=row["code"],
            name=row["name"],
            description=row["description"],
            difficulty=DifficultyLevel(row["difficulty"]),
            duration=row["duration"],
            status=CourseStatus(row["status"]),
            prerequisites=self._get_prerequisites(row["code"]),
        )
```

**Key pattern:** Every repository has a `_row_to_<model>()` private
method that converts a raw SQLite row into a typed model object.
All queries go through this method — enum strings are always converted
back to enum objects at the repository boundary.

### InMemoryUserRepository

Used in unit tests to avoid SQLite overhead:

```python
class InMemoryUserRepository:
    """
    Dictionary-backed implementation of the same interface
    as SQLiteUserRepository. No disk I/O — instant in tests.
    """

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id = 1

    def create_user(self, user: User) -> User:
        user.id = self._next_id
        self._next_id += 1
        self._users[user.id] = user
        return user
```

---

## 8. Service Layer

**Folder:** `services/`

The business logic layer. Shared identically by both UIs.
Services are wired up via dependency injection in the app factory.

### Service Map

| Service | File | Responsibility |
|---------|------|---------------|
| `CourseService` | `course_service.py` | Course CRUD, lifecycle, prerequisite graph mutations |
| `EnrollmentService` | `enrollment_service.py` | Enrollment lifecycle + prerequisite validation |
| `ProgressService` | `progress_service.py` | Progress tracking + completion rates |
| `AnalyticsService` | `analytics_service.py` | Read-only reports and statistics |
| `LearningPathService` | `learning_path_service.py` | Path generation, roadmaps |
| `RecommendationService` | `recommendation_service.py` | Personalized scored recommendations |
| `PriorLearningService` | `prior_learning_service.py` | PLR workflow orchestration |
| `AccountService` | `account_service.py` | Registration approval workflow |
| `ProfileService` | `profile_service.py` | Profile updates + password changes |

### Dependency Injection

Services receive all dependencies through their constructors.
No service creates its own repositories or graphs — they are
injected at startup.

```python
class EnrollmentService:

    def __init__(
        self,
        learner_repo:     SQLiteLearnerRepository,
        course_repo:      SQLiteCourseRepository,
        enrollment_repo:  SQLiteEnrollmentRepository,
        progress_repo:    SQLiteProgressRepository,
        validator:        PrerequisiteValidator,
        notification_repo: SQLiteNotificationRepository,
    ):
        self._learner_repo     = learner_repo
        self._course_repo      = course_repo
        self._enrollment_repo  = enrollment_repo
        self._progress_repo    = progress_repo
        self._validator        = validator
        self._notification_repo = notification_repo
```

**Why dependency injection?**
- Testable — swap real repos for in-memory fakes in tests
- Flexible — swap SQLite for PostgreSQL by injecting a different repo
- Explicit — every service's dependencies are visible at a glance

### Service Wiring (App Factory)

Both UIs call a shared factory function that creates all services
against one shared `Database` instance:

```python
def create_services(db: Database) -> dict:
    """
    Wire up all services.
    Called once at startup by both gui/app.py and webapp/__init__.py.
    """
    graph   = CourseGraph()
    detector = CycleDetector(graph)
    finder  = PathFinder(graph)
    sorter  = TopologicalSorter(graph)
    validator = PrerequisiteValidator(graph)

    user_repo       = SQLiteUserRepository(db)
    course_repo     = SQLiteCourseRepository(db)
    learner_repo    = SQLiteLearnerRepository(db)
    enrollment_repo = SQLiteEnrollmentRepository(db)
    progress_repo   = SQLiteProgressRepository(db)
    plr_repo        = SQLitePriorLearningRepository(db)
    notif_repo      = SQLiteNotificationRepository(db)
    cancel_repo     = SQLiteCancellationRepository(db)

    # Load graph from database on startup
    courses = course_repo.get_all_courses()
    prereqs = course_repo.get_all_prerequisites()
    graph.build_from_courses(
        [c.code for c in courses], prereqs
    )

    return {
        "course":        CourseService(course_repo, graph, detector, sorter),
        "enrollment":    EnrollmentService(learner_repo, course_repo,
                             enrollment_repo, progress_repo,
                             validator, notif_repo),
        "progress":      ProgressService(progress_repo, enrollment_repo),
        "analytics":     AnalyticsService(course_repo, learner_repo,
                             enrollment_repo, progress_repo),
        "learning_path": LearningPathService(graph, finder, sorter,
                             learner_repo, course_repo, enrollment_repo),
        "recommendation":RecommendationService(graph, learner_repo,
                             course_repo, enrollment_repo),
        "prior_learning":PriorLearningService(plr_repo, enrollment_repo,
                             notif_repo, learner_repo),
        "account":       AccountService(user_repo, learner_repo, notif_repo),
        "profile":       ProfileService(user_repo, learner_repo, notif_repo),
    }
```

---

## 9. Desktop GUI Layer

**Folder:** `gui/`

Tkinter desktop application. Role-based screens routed by
`main_window.py` based on `SessionManager.current_user().role`.

### Structure

```
gui/
├── app.py              ← entry point: create_services() + LoginWindow
├── main_window.py      ← shell: header + sidebar + content frame
├── login_window.py     ← login form + register link
├── register_window.py  ← self-registration form
├── admin_dashboard.py
├── learner_dashboard.py
├── analytics_dashboard.py
├── admin/              ← admin-only screens
├── instructor/         ← instructor-only screens
├── learner/            ← learner-only screens
├── analyst/            ← analyst-only screens
├── profile/            ← profile screens (all roles)
├── widgets/            ← reusable Tkinter components
└── dialogs/            ← confirm / info / error dialogs
```

### Screen Routing

```python
class MainWindow:

    def _build_sidebar(self):
        role = SessionManager().current_user().role

        if role == UserRole.ADMIN:
            nav_items = [
                ("Dashboard",       self._show_admin_dashboard),
                ("Pending Accounts",self._show_pending_registrations),
                ("Courses",         self._show_course_management),
                ("Course Approvals",self._show_course_approvals),
                ("Prerequisites",   self._show_prerequisite_management),
                ("Learners",        self._show_learner_management),
                ("Users",           self._show_user_management),
                ("Prior Learning",  self._show_plr_approval),
                ("Analytics",       self._show_analytics),
                ("My Profile",      self._show_profile),
            ]

        elif role == UserRole.LEARNER:
            nav_items = [
                ("Dashboard",       self._show_learner_dashboard),
                ("My Courses",      self._show_enrollments),
                ("Learning Path",   self._show_learning_path),
                ("Progress",        self._show_progress),
                ("Prior Learning",  self._show_prior_learning),
                ("Recommendations", self._show_recommendations),
                ("My Profile",      self._show_profile),
            ]
        # ... instructor, analyst ...
```

### Reusable Widgets

| Widget | File | Purpose |
|--------|------|---------|
| `Sidebar` | `widgets/sidebar.py` | Nav with hover + selected states |
| `CourseTable` | `widgets/course_table.py` | Sortable `ttk.Treeview` |
| `GraphView` | `widgets/graph_view.py` | Canvas prerequisite diagram |
| `PasswordStrengthMeter` | `widgets/password_strength.py` | Live 0–100 meter |
| `confirm()` | `dialogs/confirm_dialog.py` | Yes / No dialog |
| `show_error()` | `dialogs/confirm_dialog.py` | Error message |
| `show_info()` | `dialogs/confirm_dialog.py` | Info message |

### Session (Desktop)

```python
# Login
session = SessionManager()
session.login(user)

# Check role in any screen
user = SessionManager().current_user()
if user.role != UserRole.ADMIN:
    show_error("Access denied")
    return

# Logout
SessionManager().logout()
```

---

## 10. Web Application Layer

**Folder:** `webapp/`

Flask server-rendered application. One Blueprint per role plus shared
`auth` and `profile` blueprints.

### Structure

```
webapp/
├── __init__.py         ← app factory: create_app()
├── auth.py             ← /login, /logout, /register
├── auth_utils.py       ← role_required(), login_required decorators
├── admin.py            ← /admin/* Blueprint
├── instructor.py       ← /instructor/* Blueprint
├── learner.py          ← /learner/* Blueprint
├── analyst.py          ← /analyst/* Blueprint
├── profile.py          ← /profile/* Blueprint
├── static/
│   ├── style.css
│   └── js/
│       └── chart.umd.min.js   ← Chart.js local bundle
└── templates/
    ├── base.html              ← base layout + nav + {% block scripts %}
    ├── _flashes.html          ← flash message partial
    ├── auth/                  ← login, register, pending
    ├── admin/                 ← 8 admin templates
    ├── instructor/            ← 4 instructor templates
    ├── learner/               ← 6 learner templates
    ├── analyst/               ← 5 analyst templates
    ├── profile/               ← profile view
    └── errors/                ← 403, 404
```

### Blueprint Registration

```python
def create_app(services: dict) -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

    # Store services on app for blueprint access
    app.config["SERVICES"] = services

    # Register blueprints
    from webapp.auth       import auth_bp
    from webapp.admin      import admin_bp
    from webapp.instructor import instructor_bp
    from webapp.learner    import learner_bp
    from webapp.analyst    import analyst_bp
    from webapp.profile    import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp,      url_prefix="/admin")
    app.register_blueprint(instructor_bp, url_prefix="/instructor")
    app.register_blueprint(learner_bp,    url_prefix="/learner")
    app.register_blueprint(analyst_bp,    url_prefix="/analyst")
    app.register_blueprint(profile_bp,    url_prefix="/profile")

    return app
```

### Auth Utils (`webapp/auth_utils.py`)

```python
def login_required(f):
    """Redirect to /login if no session['user_id']."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Return 403 if logged-in user's role is not in allowed roles."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            user = _get_current_user()
            if user.role.value not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
```

**Usage:**
```python
# webapp/admin.py
@admin_bp.route("/courses")
@role_required("ADMIN")
def courses():
    ...

# webapp/analyst.py
@analyst_bp.route("/")
@role_required("ANALYST", "ADMIN")   # both roles allowed
def dashboard():
    ...
```

### Session (Web)

```python
# Login — store user ID in signed cookie
session["user_id"] = user.id
session["role"]    = user.role.value

# Read in route
user_id = session.get("user_id")

# Logout — clear cookie
session.clear()
```

### Template Structure

```html
<!-- base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}LMPTS{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <nav><!-- role-based nav --></nav>

    {% include '_flashes.html' %}

    <main>
        {% block content %}{% endblock %}
    </main>

    <!-- Page-specific JS loaded here (Chart.js etc.) -->
    {% block scripts %}{% endblock %}
</body>
</html>

<!-- analyst/dashboard.html -->
{% extends "base.html" %}

{% block content %}
<!-- 5 dashboard sections -->
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/chart.umd.min.js') }}"></script>
<script>
    // Chart initialization with data from Jinja
    const labels = {{ chart_data.labels | tojson }};
    new Chart(ctx, { ... });
</script>
{% endblock %}
```

---

## 11. Dual-UI Strategy

Both UIs are built on the same service layer. This is the central
architectural decision of LMPTS.

```
gui/app.py                          run_web.py
     │                                   │
     │ calls                             │ calls
     ▼                                   ▼
create_services(db)         ←←←←←  create_services(db)
     │                      same         │
     │ returns               function    │ returns
     ▼                                   ▼
{course_service,            ←←←←←  {course_service,
 enrollment_service,         same    enrollment_service,
 ...}                       objects  ...}
```

**Result:** Business rules are implemented exactly once.
A bug fix in `EnrollmentService.enroll_learner()` fixes both
the desktop and web interfaces simultaneously.

### Where They Differ

| Concern | Desktop | Web |
|---------|---------|-----|
| Session storage | `SessionManager` singleton | Flask `session['user_id']` cookie |
| Auth gating | Role check in `MainWindow._build_sidebar()` | `role_required()` decorator |
| Data display | Tkinter `ttk.Treeview`, `Canvas` | Jinja2 tables, `<canvas>` |
| Charts | matplotlib `Figure` | Chart.js (local bundle) |
| Flash messages | `tkinter.messagebox` / custom dialogs | `flask.flash()` + `_flashes.html` |
| Error pages | Custom dialog popup | `errors/403.html`, `errors/404.html` |
| Cancellation workflow | ✅ Fully implemented | ⚠️ Not yet ported |

### Feature Parity Gap

The cancellation request workflow exists only in the desktop GUI.
The web app currently has no routes for:
- `POST /learner/enrollments/<id>/cancel-request`
- `GET  /instructor/cancellations`
- `POST /instructor/cancellations/<id>/approve`
- `POST /instructor/cancellations/<id>/reject`

This is a known gap documented for future implementation.

---

## 12. Design Patterns

### Repository Pattern

**Where:** `repository/*.py`
**Purpose:** Decouples business logic from the database engine.

```
Service ──► Repository Interface ──► SQLite Implementation
                                └──► InMemory Implementation (tests)
```

Swapping SQLite for PostgreSQL requires only a new repository
implementation — no service code changes.

### Singleton Pattern

**Where:** `auth/session_manager.py`
**Purpose:** One active user session per desktop process.

```python
s1 = SessionManager()
s2 = SessionManager()
assert s1 is s2  # True — same object
```

### Factory Pattern

**Where:** `create_services()` in both `gui/app.py` and
`webapp/__init__.py`
**Purpose:** Centralized service wiring — all dependencies
resolved in one place.

### Dependency Injection

**Where:** All service constructors
**Purpose:** Services receive all dependencies via constructor
arguments rather than creating them. Enables easy testing.

### Observer Pattern

**Where:** Notification system across all services
**Purpose:** Decouple event producers (PLR approval) from
event consumers (learner notification).

```python
# PriorLearningService notifies without knowing who reads it
self._notification_repo.create(
    user_id=learner.user_id,
    message=f"Your PLR for {course_code} was approved.",
    notification_type="SUCCESS"
)
```

### Strategy Pattern

**Where:** `algorithms/recommendation.py`
**Purpose:** Scoring weights are configurable — different
weight distributions can be plugged in without rewriting
the engine.

### State Machine Pattern

**Where:** `core/enrollment.py`, `EnrollmentService`
**Purpose:** Enrollment status transitions are explicit
and validated — you cannot jump from `ENROLLED` to
`COMPLETED` without going through `IN_PROGRESS`.

### Template Method Pattern

**Where:** Repository base classes
**Purpose:** Define the interface once, implement per-database.

---

## 13. Data Flow Walkthroughs

### Flow 1: Learner Enrolls in a Course

```
1. Learner clicks "Enroll" on CS201 in the GUI/Web
         │
2. GUI:  EnrollmentService.enroll_learner(learner_id=3, "CS201")
   Web:  Same call from Flask route
         │
3. EnrollmentService:
   a. LearnerRepo.get_learner(3)          → verify exists
   b. CourseRepo.get_course("CS201")      → verify exists + PUBLISHED
   c. EnrollmentRepo.find(3, "CS201")     → check no duplicate
   d. LearnerRepo.get_completed(3)        → {"CS101"}
   e. LearnerRepo.get_transfers(3)        → {"CS102"}
   f. Build LearnerCredits(
          completed={"CS101"},
          transfer_credits={"CS102"})
   g. PrerequisiteValidator.can_enroll(
          credits, "CS201")
      → graph.get_prerequisites("CS201") = {"CS101","CS102"}
      → missing = {"CS101","CS102"} - {"CS101","CS102"} = ∅
      → ValidationResult(can_enroll=True)
         │
4. with db.transaction():
   a. INSERT INTO enrollments ...         → id=42, status=ENROLLED
   b. INSERT INTO course_progress ...     → 0%, NOT_STARTED
   Both committed atomically
         │
5. Return EnrollmentResult(success=True, enrollment=Enrollment(id=42))
         │
6. GUI shows success toast / Web flashes success + redirects
```

---

### Flow 2: Admin Adds a Prerequisite (with Cycle Check)

```
1. Admin types "CS101 requires CS301" in prerequisite form
         │
2. CourseService.add_prerequisite("CS101", "CS301")
         │
3. CourseRepo.get_course("CS101")   → exists ✓
   CourseRepo.get_course("CS301")   → exists ✓
         │
4. CycleDetector.would_create_cycle("CS301", "CS101")
   → Copy graph
   → Add edge CS301 → CS101 to copy
   → DFS on copy:
       CS301 (GREY)
         → CS201 (GREY)
           → CS101 (GREY)
             → CS301 already GREY → BACK EDGE → CYCLE
   → Returns True
         │
5. raise CircularDependencyError(
       "Adding CS301 → CS101 creates a cycle: CS101 → CS201 → CS301 → CS101"
   )
         │
6. Real graph unchanged
   Database unchanged
   GUI shows error: "Cannot add prerequisite: circular dependency detected"
```

---

### Flow 3: PLR Approval Auto-Grants Credit

```
1. Admin clicks "Approve" on PLR request #7
         │
2. PriorLearningService.admin_decision(
       request_id=7,
       decision="APPROVED",
       note="Evidence verified",
       admin_id=1
   )
         │
3. PLRRepo.get_request(7)             → PriorLearningRequest
   Validate status == INSTRUCTOR_REVIEWED
         │
4. PLRRepo.update_status(7, "APPROVED", admin_note, admin_id)
         │
5. EnrollmentService.transfer_credit(
       learner_id=request.learner_id,
       course_code=request.course_code
   )
   → INSERT COMPLETED enrollment + 100% progress (atomic)
         │
6. NotificationRepo.create(
       user_id=learner.user_id,
       message="Your PLR for CS201 was APPROVED. Credit granted.",
       type="SUCCESS"
   )
         │
7. Next time learner tries to enroll in CS301:
   PrerequisiteValidator sees CS201 in completed_courses
   → can_enroll = True
```

---

### Flow 4: Analytics Dashboard Request (Web)

```
1. Browser GET /analyst/
         │
2. @role_required("ANALYST", "ADMIN") → session["role"] check ✓
         │
3. analyst.dashboard() route:
   services = current_app.config["SERVICES"]
   analytics = services["analytics"]
         │
4. Calls (all read-only, no caching):
   a. analytics.system_overview()
   b. analytics.student_performance_report()
   c. analytics.score_bucket_distribution()
   d. analytics.performance_trend(months=6)
   e. analytics.course_completion_breakdown()
   f. analytics.course_completion_by_course()
   g. analytics.enrollment_monthly_trend(months=6)
   h. analytics.enrollment_summary_metrics()
   i. analytics.instructor_analytics(instructors, courses)
         │
5. Pass all data to template:
   render_template("analyst/dashboard.html",
       overview=overview,
       performance=performance,
       ...)
         │
6. Jinja2 renders HTML with embedded JSON:
   const labels = {{ chart_data.labels | tojson }};
         │
7. Browser receives HTML, Chart.js reads embedded JSON,
   renders 10 charts client-side
```

---

## 14. Error Handling Strategy

### Three Levels of Error Handling

```
Level 1 — Algorithm layer (raises exceptions):
    CircularDependencyError, ValueError
    → Caught by service layer

Level 2 — Service layer (raises or returns soft result):
    CourseNotFoundError, LearnerNotFoundError, ValidationError
    → Raised: caller must handle
    EnrollmentResult(success=False)
    → Soft failure: caller checks result.success

Level 3 — UI layer (shows user-friendly message):
    Desktop: show_error(str(e))
    Web:     flash(str(e), "error") or abort(403)
```

### Soft vs. Hard Failures

| Scenario | Mechanism | Reason |
|----------|-----------|--------|
| Enrollment missing prereqs | `EnrollmentResult(success=False)` | Expected user error — show helpful message |
| Course not found | `CourseNotFoundError` | Programming error — should not happen in normal flow |
| Circular dependency | `CircularDependencyError` | Admin data error — must be explicit |
| Wrong password | `AuthenticationError` | Security — must be raised, not silently ignored |
| Analytics on empty db | Returns 0 / empty list | Graceful degradation — never crash on no data |

---

## 15. Security Design

| Concern | Solution |
|---------|---------|
| **Password storage** | bcrypt with unique salt per hash — never plain text |
| **Timing attacks** | `bcrypt.checkpw()` uses constant-time comparison |
| **Username enumeration** | Same error message for "not found" and "wrong password" |
| **Session fixation (web)** | Flask signed cookie — tamper-evident |
| **Session isolation (web)** | Each request reads `session['user_id']` — no shared singleton |
| **Role enforcement (desktop)** | `SessionManager.current_user().role` checked in `MainWindow` |
| **Role enforcement (web)** | `role_required()` decorator on every blueprint route |
| **SQL injection** | All queries use parameterized `?` placeholders — no string concatenation |
| **Cascade deletes** | `ON DELETE CASCADE` on all FKs — no orphan data |
| **Cycle injection** | `CycleDetector.would_create_cycle()` runs before every prerequisite write |
| **Duplicate enrollment** | `UNIQUE(learner_id, course_code)` at DB level + service-level check |

---

## 16. Testing Architecture

### Test Isolation Strategy

```
Each test gets its own:
    tmp_path/test.db  ← fresh SQLite file via pytest tmp_path fixture
    Database(path)    ← wired to the temp file
    SessionManager.reset()  ← cleared before every test (autouse)

No test shares state with another test.
No test touches data/lmpts.db.
```

### Test Layers

```
tests/
├── test_models.py          ← core model unit tests (no DB)
├── test_auth_service.py    ← auth with InMemoryUserRepository
├── test_course.py          ← Course model unit tests
├── test_enrollment.py      ← Enrollment state machine
├── test_learner.py         ← Learner model
├── test_password_manager.py← bcrypt hashing tests
├── test_session_manager.py ← singleton + reset tests
├── test_services.py        ← general service tests
├── test_integration.py     ← full cross-layer workflows
├── algorithms/             ← one file per algorithm class
│   ├── test_graph.py
│   ├── test_cycle_detection.py
│   ├── test_topological_sort.py
│   ├── test_path_finder.py
│   ├── test_prerequisite_validator.py
│   └── test_recommendation.py
├── repository/             ← real SQLite with tmp_path
│   ├── test_sqlite_repositories.py
│   └── test_cancellation_repo.py
└── services/               ← service tests with real repos
    ├── test_analytics_service.py   (33 tests, empty-db guards)
    ├── test_course_service.py
    ├── test_enrollment_service.py
    ├── test_learning_path_service.py
    └── test_progress_service.py
```

### Key Testing Patterns

```python
# Pattern 1 — Isolated temp database
@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.initialize()
    return database

# Pattern 2 — Reset singleton between tests
@pytest.fixture(autouse=True)
def reset_session():
    SessionManager.reset()
    yield
    SessionManager.reset()

# Pattern 3 — InMemory for pure unit tests
@pytest.fixture
def auth_service():
    repo = InMemoryUserRepository()
    pm   = PasswordManager()
    return AuthService(repo, pm)

# Pattern 4 — Empty database analytics guard
def test_system_overview_empty_database(db):
    """No division-by-zero when database has no data."""
    analytics = AnalyticsService(
        SQLiteCourseRepository(db),
        SQLiteLearnerRepository(db),
        SQLiteEnrollmentRepository(db),
        SQLiteProgressRepository(db),
    )
    overview = analytics.system_overview()
    assert overview["completion_rate"] == 0.0   # not ZeroDivisionError
    assert overview["total_courses"] == 0
```

---

## 17. Key Design Decisions

### Decision 1 — Shared Service Layer

Both UIs call the same service objects against the same database.

**Alternatives considered:**
- Duplicate services per UI — rejected: logic would drift apart
- REST API between UIs — rejected: over-engineered for this scope

**Consequence:** Any service bug is fixed once and both UIs benefit.

---

### Decision 2 — Two Graphs (Forward + Reverse)

`CourseGraph` maintains both `graph` and `reverse_graph`.

**Alternatives considered:**
- Single forward graph, compute reverse on demand — rejected:
  O(n) reverse computation on every prerequisite check
- Store only reverse graph — rejected: path finder needs forward

**Consequence:** O(1) lookup in both directions at the cost of
double memory (negligible for course counts in the hundreds).

---

### Decision 3 — Kahn's Algorithm over Recursive DFS Sort

Topological sort uses Kahn's (iterative BFS) not recursive DFS.

**Reason:** Recursive DFS risks stack overflow on very deep
prerequisite chains. Kahn's is iterative and handles arbitrarily
deep graphs safely.

---

### Decision 4 — Prerequisites in Junction Table

`PREREQUISITES(course_code, prerequisite_code)` not a JSON column
on `COURSES`.

**Alternatives considered:**
- JSON column `courses.prerequisites = '["CS101","CS102"]'` — rejected:
  cannot use SQL joins, harder to query, harder to enforce FK integrity

**Consequence:** Clean relational design, efficient SQL queries,
FK cascade deletes work correctly.

---

### Decision 5 — Derived Course Sets for Learner

`Learner.completed_courses` and `Learner.current_courses` are not
stored — they are queried from `ENROLLMENTS` every time.

**Alternatives considered:**
- Store sets in `LEARNERS` table — rejected: would create two sources
  of truth that could diverge

**Consequence:** Single source of truth. Slightly more reads,
but correctness is guaranteed.

---

### Decision 6 — Soft Failure for Enrollment

`enroll_learner()` returns `EnrollmentResult(success=False)` instead
of raising an exception for missing prerequisites.

**Reason:** Missing prerequisites are an **expected user scenario**,
not a programming error. The result object carries the missing course
list which the UI uses to show a helpful message and suggest a path.

**Contrast:** `CourseNotFoundError` is raised because a route
calling `enroll_learner()` with an invalid code indicates a bug in
the UI, not a user error.

---

### Decision 7 — Chart.js Bundled Locally

`webapp/static/js/chart.umd.min.js` is served locally, not from CDN.

**Reason:** Eliminates CDN availability dependency. Works offline
and in restricted network environments.

---

### Decision 8 — `None` not `0` for Missing Month Data

`performance_trend()` returns `None` for months with no completions.

**Reason:** A month with zero completions is meaningfully different
from a month with completions averaging 0. Returning `None` lets the
Chart.js consumer render a genuine gap in the line rather than a
misleading data point at zero.