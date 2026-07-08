

```markdown
# LMPTS — Learning Management & Prerequisite Tracking System

## Complete Project Documentation

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Installation Guide](#5-installation-guide)
6. [Database Design](#6-database-design)
7. [Core Models](#7-core-models)
8. [Authentication System](#8-authentication-system)
9. [Repository Layer](#9-repository-layer)
10. [Algorithm Engine](#10-algorithm-engine)
11. [Service Layer](#11-service-layer)
12. [GUI Application](#12-gui-application)
13. [User Roles and Responsibilities](#13-user-roles-and-responsibilities)
14. [Approval Workflows](#14-approval-workflows)
15. [Prior Learning / Transfer Credit System](#15-prior-learning--transfer-credit-system)
16. [Account Activation System](#16-account-activation-system)
17. [Profile Management](#17-profile-management)
18. [Notification System](#18-notification-system)
19. [Analytics and Reporting](#19-analytics-and-reporting)
20. [Testing](#20-testing)
21. [Running the Application](#21-running-the-application)
22. [Default Credentials](#22-default-credentials)
23. [UML Diagrams](#23-uml-diagrams)
24. [Future Enhancements](#24-future-enhancements)

---

## 1. Project Overview

### What is LMPTS?

LMPTS (Learning Management & Prerequisite Tracking System) is a desktop application
that manages academic courses, tracks prerequisite dependencies between courses,
manages learner enrollments, and provides intelligent learning path recommendations.

### Why was it built?

Traditional learning management systems lack intelligent prerequisite tracking.
LMPTS solves this by combining:

- **Course prerequisite graph management** with cycle detection
- **Intelligent learning path generation** using BFS and topological sorting
- **Transfer credit and prior learning recognition** for learners from other platforms
- **Role-based access control** for administrators, instructors, learners, and analysts
- **Real-time analytics** for monitoring learner progress and course effectiveness

### Key Differentiators

| Feature | Traditional LMS | LMPTS |
|---------|----------------|-------|
| Prerequisite management | Manual checking | Automated graph-based validation |
| Cycle detection | Not available | DFS-based circular dependency detection |
| Learning path | Manual planning | Auto-generated using topological sort + BFS |
| Transfer credits | Simple checkbox | Full workflow: learner → instructor → admin |
| Recommendations | None | Scored multi-factor recommendation engine |
| Account activation | Auto-active | Admin approval workflow |
| Analytics | Basic reports | Bottleneck detection, chain analysis |

### Who uses it?

| Role | Primary Actions |
|------|----------------|
| **Administrator** | Manages users, courses, prerequisites, approves registrations and transfer credits |
| **Instructor** | Creates courses, monitors learners, reviews prior learning requests |
| **Learner** | Enrolls in courses, tracks progress, submits transfer credit requests |
| **Analyst** | Views reports, identifies bottlenecks, analyzes completion trends |

---

## 2. System Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────┐
│              GUI Layer (Tkinter)                 │
│   Login │ Admin │ Learner │ Instructor │ Analyst │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              Service Layer                       │
│   CourseService       EnrollmentService          │
│   ProgressService     AnalyticsService           │
│   LearningPathService RecommendationService      │
│   PriorLearningService AccountService            │
│   ProfileService                                 │
└──────────┬──────────────────────┬───────────────┘
           │                      │
┌──────────▼──────────┐  ┌────────▼──────────────┐
│   Algorithm Engine   │  │   Repository Layer     │
│   CourseGraph        │  │   UserRepo             │
│   CycleDetector(DFS) │  │   CourseRepo           │
│   PathFinder (BFS)   │  │   LearnerRepo          │
│   TopologicalSorter  │  │   EnrollmentRepo       │
│   PrereqValidator    │  │   ProgressRepo         │
│   RecommendEngine    │  │   PriorLearningRepo    │
└─────────────────────┘  │   NotificationRepo     │
                          └────────┬──────────────┘
                                   │
                          ┌────────▼──────────────┐
                          │   Core Models + Auth   │
                          │   User, Course, Learner│
                          │   Enrollment, Enums    │
                          │   PasswordManager      │
                          │   SessionManager       │
                          └────────┬──────────────┘
                                   │
                          ┌────────▼──────────────┐
                          │   SQLite Database      │
                          │   data/lmpts.db        │
                          └───────────────────────┘
```

### Design Patterns Used

| Pattern | Where Used | Purpose |
|---------|-----------|---------|
| **Repository Pattern** | `repository/*.py` | Decouples business logic from database |
| **Singleton Pattern** | `SessionManager` | One active session per application |
| **Factory Pattern** | `create_*_service()` | Production service creation |
| **Dependency Injection** | All services | Constructor injection for testing |
| **Observer Pattern** | Notifications | Notify users of system events |
| **Strategy Pattern** | Recommendation scoring | Pluggable scoring weights |
| **Template Method** | Abstract repositories | Define interface, implement per-DB |

### Data Flow Example: Learner Enrolls in a Course

```
Learner clicks "Enroll" in GUI
         ↓
GUI calls EnrollmentService.enroll_learner()
         ↓
EnrollmentService calls LearnerRepo.get_learner()
    → Verify learner exists
         ↓
EnrollmentService calls CourseRepo.get_course()
    → Verify course exists and is PUBLISHED
         ↓
EnrollmentService calls PrerequisiteValidator.can_enroll()
    → Build LearnerCredits from completed enrollments
    → Check all direct prerequisites are satisfied
    → If any missing → return EnrollmentResult(success=False)
         ↓
EnrollmentService starts database TRANSACTION
    → Insert into enrollments table
    → Insert into course_progress table
    → Both succeed or both rollback
         ↓
EnrollmentResult(success=True) returned to GUI
         ↓
GUI shows success message and refreshes the course list
```

---

## 3. Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.11+ | Core application |
| GUI Framework | Tkinter (ttk) | Built-in | Desktop interface |
| Database | SQLite | Built-in | Data persistence |
| Password Hashing | bcrypt | 4.x | Secure password storage |
| Charts | matplotlib | 3.x | Analytics visualizations |
| Testing | pytest | 7.x+ | Unit and integration tests |
| Coverage | pytest-cov | 7.x | Test coverage reports |

### Install Dependencies

```bash
pip install bcrypt pytest pytest-cov matplotlib
```

### Verify Installation

```bash
python -c "import bcrypt; print('bcrypt:', bcrypt.__version__)"
python -c "import pytest; print('pytest:', pytest.__version__)"
python -c "import matplotlib; print('matplotlib:', matplotlib.__version__)"
```

---

## 4. Project Structure

```
C:\LMPTS\
│
├── core/                           # Domain models and constants
│   ├── __init__.py
│   ├── enums.py                    # All enumerations
│   ├── exceptions.py               # Custom exception hierarchy
│   ├── user.py                     # User model with profile
│   ├── course.py                   # Course model with prerequisites
│   ├── learner.py                  # Learner model
│   ├── enrollment.py               # Enrollment state machine
│   ├── course_progress.py          # Progress tracking model
│   ├── prior_learning_request.py   # PLR model
│   └── notification.py             # Notification model
│
├── auth/                           # Authentication system
│   ├── __init__.py
│   ├── password_manager.py         # bcrypt hashing (class)
│   ├── auth_service.py             # Login/register/password logic
│   ├── session_manager.py          # Singleton session
│   └── user_repository.py          # Abstract UserRepository interface
│
├── repository/                     # Database access layer
│   ├── __init__.py
│   ├── database.py                 # Database class + migrations v1-v4
│   ├── user_repo.py                # SQLite + InMemory user repos
│   ├── course_repo.py              # Course + prerequisites repo
│   ├── learner_repo.py             # Learner repo (derives courses from enrollments)
│   ├── enrollment_repo.py          # Enrollment + Progress repos
│   └── prior_learning_repo.py      # PLR + Notification repos
│
├── algorithms/                     # Graph algorithms
│   ├── __init__.py
│   ├── graph.py                    # CourseGraph (forward + reverse)
│   ├── cycle_detection.py          # DFS cycle detector
│   ├── path_finder.py              # BFS shortest path + study order
│   ├── topological_sort.py         # Kahn's algorithm
│   ├── prerequisite_validator.py   # Enrollment eligibility checker
│   └── recommendation.py           # Multi-factor recommendation engine
│
├── services/                       # Business logic layer
│   ├── __init__.py
│   ├── course_service.py           # Course CRUD + lifecycle + prereqs
│   ├── enrollment_service.py       # Enrollment + transfer + exemption
│   ├── progress_service.py         # Progress tracking + completion rates
│   ├── analytics_service.py        # Reports + bottleneck detection
│   ├── learning_path_service.py    # Path generation + roadmaps
│   ├── recommendation_service.py   # Personalized recommendations
│   ├── prior_learning_service.py   # PLR workflow orchestration
│   ├── account_service.py          # Registration approval workflow
│   └── profile_service.py          # Profile management + password
│
├── gui/                            # Desktop GUI (Tkinter)
│   ├── __init__.py
│   ├── app.py                      # Application entry point
│   ├── login_window.py             # Login screen with register link
│   ├── register_window.py          # Self-registration form
│   ├── main_window.py              # Header + sidebar + content shell
│   ├── admin_dashboard.py          # Admin overview statistics
│   ├── learner_dashboard.py        # Learner progress overview
│   ├── analytics_dashboard.py      # Analytics with charts
│   │
│   ├── admin/                      # Admin-specific screens
│   │   ├── __init__.py
│   │   ├── course_management.py    # CRUD + publish + archive
│   │   ├── prerequisite_management.py  # Graph view + text view
│   │   ├── learner_management.py   # Transfer credits + exemptions
│   │   ├── user_management.py      # Create/delete users
│   │   ├── pending_registrations.py    # Approve/reject accounts
│   │   ├── plr_approval.py        # Final PLR decisions
│   │   └── course_approvals.py    # Approve instructor courses
│   │
│   ├── learner/                    # Learner-specific screens
│   │   ├── __init__.py
│   │   ├── enrollments.py         # My enrollments + start/complete
│   │   ├── progress.py            # Progress bars + learning path
│   │   ├── recommendations.py    # Scored recommendation cards
│   │   └── prior_learning.py     # Submit PLR + track status
│   │
│   ├── instructor/                 # Instructor-specific screens
│   │   ├── __init__.py
│   │   ├── dashboard.py           # Stats + notifications
│   │   ├── course_manager.py      # Create/submit courses
│   │   ├── learner_monitor.py     # Monitor + grade learners
│   │   └── plr_review.py         # Review PLR requests
│   │
│   ├── analyst/                    # Analyst-specific screens
│   │   ├── __init__.py
│   │   └── analytics.py          # Reports + bottlenecks + chains
│   │
│   ├── profile/                    # Profile management (all roles)
│   │   ├── __init__.py
│   │   ├── profile_screen.py     # Main profile with tabs
│   │   ├── personal_info_form.py # Name/email/bio editor
│   │   └── password_change_form.py # Password change with strength
│   │
│   ├── widgets/                    # Reusable UI components
│   │   ├── __init__.py
│   │   ├── sidebar.py            # Navigation sidebar
│   │   ├── course_table.py       # Sortable course Treeview
│   │   ├── graph_view.py         # Canvas prerequisite diagram
│   │   └── password_strength.py  # Live strength meter
│   │
│   └── dialogs/                    # Dialog helpers
│       ├── __init__.py
│       └── confirm_dialog.py      # confirm/error/info/warning
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── test_models.py             # Person 1: Core model tests
│   ├── test_algorithms.py         # Person 3: Algorithm tests
│   │
│   ├── repository/                 # Person 2: Database tests
│   │   ├── __init__.py
│   │   └── test_sqlite_repositories.py
│   │
│   ├── algorithms/                 # Person 3: Algorithm tests (detailed)
│   │   ├── __init__.py
│   │   ├── test_graph.py
│   │   ├── test_cycle_detection.py
│   │   ├── test_topological_sort.py
│   │   ├── test_path_finder.py
│   │   ├── test_prerequisite_validator.py
│   │   └── test_recommendation.py
│   │
│   └── services/                   # Person 4: Service tests
│       ├── __init__.py
│       ├── test_course_service.py
│       ├── test_enrollment_service.py
│       ├── test_progress_service.py
│       ├── test_analytics_service.py
│       └── test_learning_path_service.py
│
├── data/                           # Database files
│   └── lmpts.db                   # SQLite database
│
├── pytest.ini                      # Test configuration
├── setup_database.py               # Database initialization script
├── launch_role.py                  # Launch specific role dashboard
├── launch_all.py                   # Launch all 4 role dashboards
├── multi_login.py                  # Launch multiple login windows
└── README.md                       # This documentation
```

---

## 5. Installation Guide

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Step-by-Step Installation

```bash
# 1. Clone or create the project directory
mkdir C:\LMPTS
cd C:\LMPTS

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate

# 4. Install dependencies
pip install bcrypt pytest pytest-cov matplotlib

# 5. Initialize the database
python setup_database.py

# 6. Run all tests
python -m pytest tests/ -v

# 7. Launch the application
python gui/app.py
```

### Verify Installation

```bash
python -c "
import bcrypt, pytest, matplotlib, tkinter, sqlite3
print('All dependencies OK')
print(f'Python:     {__import__(\"sys\").version}')
print(f'bcrypt:     {bcrypt.__version__}')
print(f'pytest:     {pytest.__version__}')
print(f'matplotlib: {matplotlib.__version__}')
print(f'SQLite:     {sqlite3.sqlite_version}')
"
```

---

## 6. Database Design

### Schema Version History

| Version | Changes |
|---------|---------|
| v1 | Performance indexes on frequently queried columns |
| v2 | Prior learning requests table, course submissions table, notifications table |
| v3 | Account activation columns: is_active, account_status, rejection_reason, full_name, email |
| v4 | Profile management columns: bio, preferred_difficulty, profile_updated_at |

### Entity Relationship Diagram

```
USERS                          LEARNERS
──────────────────────         ──────────────────────
id            PK               id           PK
username      UNIQUE           user_id      FK → USERS.id
password_hash                  name
role                           email        UNIQUE
created_at
is_active                      COURSES
account_status                 ──────────────────────
rejection_reason               code         PK
full_name                      name
email                          description
bio                            difficulty
preferred_difficulty           duration
profile_updated_at             status

PREREQUISITES                  ENROLLMENTS
──────────────────────         ──────────────────────
id            PK               id            PK
course_code   FK → COURSES     learner_id    FK → LEARNERS
prerequisite_code FK → COURSES course_code   FK → COURSES
UNIQUE(course, prereq)         status
                               score
                               enrolled_at
                               completed_at
                               UNIQUE(learner, course)

COURSE_PROGRESS                PRIOR_LEARNING_REQUESTS
──────────────────────         ──────────────────────
id            PK               id            PK
learner_id    FK → LEARNERS    learner_id    FK → LEARNERS
course_code   FK → COURSES     course_code   FK → COURSES
percentage                     pathway
completion_status              evidence_description
updated_at                     external_platform
UNIQUE(learner, course)        external_score
                               status
                               instructor_recommendation
                               instructor_note
                               instructor_id
                               admin_note
                               admin_id
                               submitted_at
                               reviewed_by_instructor_at
                               decided_by_admin_at

COURSE_SUBMISSIONS             NOTIFICATIONS
──────────────────────         ──────────────────────
id            PK               id            PK
course_code   FK → COURSES     user_id       FK → USERS
instructor_id                  message
status                         notification_type
instructor_note                is_read
admin_note                     created_at
submitted_at
decided_at

SCHEMA_VERSION
──────────────────────
version
applied_at
```

### Key Design Decisions

| Decision | Reason |
|----------|--------|
| Prerequisites in junction table | Clean relational design, no JSON columns |
| Learner courses derived from enrollments | Single source of truth, no data duplication |
| Connection per operation | Safe for concurrent admin/learner access |
| WAL journal mode | Allows concurrent readers + one writer |
| ON DELETE CASCADE | Deleting a user automatically cleans up enrollments, progress |
| Temporary file databases for tests | Avoids SQLite :memory: shared-cache problems |
| Schema version tracking | Safe database migrations without data loss |

---

## 7. Core Models

### 7.1 Enumerations (core/enums.py)

All system constants are defined as Python Enum classes to prevent magic strings.

```python
# Usage: if user.role == UserRole.ADMIN:
#   instead of: if user.role == "admin":  ← error-prone
```

| Enum | Values | Used By |
|------|--------|---------|
| `DifficultyLevel` | BEGINNER, INTERMEDIATE, ADVANCED | Course, Recommendations |
| `CourseStatus` | DRAFT, PUBLISHED, ARCHIVED | Course lifecycle |
| `EnrollmentStatus` | ENROLLED, IN_PROGRESS, COMPLETED, CANCELLED | Enrollment state machine |
| `UserRole` | ADMIN, LEARNER, ANALYST, INSTRUCTOR | Authentication, authorization |
| `CompletionStatus` | NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED | Progress tracking |
| `AccountStatus` | ACTIVE, PENDING, REJECTED, INACTIVE | Registration approval |

### 7.2 Exception Hierarchy (core/exceptions.py)

```
Exception
    └── LMPTSException           ← catch-all for any LMPTS error
            ├── ValidationError
            ├── AuthenticationError
            ├── CourseNotFoundError
            ├── LearnerNotFoundError
            ├── EnrollmentError
            │       ├── DuplicateEnrollmentError
            │       └── PrerequisiteNotMetError
            └── CircularDependencyError
```

Every custom exception inherits from `LMPTSException`, allowing callers to catch
broadly (`except LMPTSException`) or precisely (`except CircularDependencyError`).

### 7.3 User Model (core/user.py)

Represents a system account with profile data.

| Attribute | Type | Description |
|-----------|------|-------------|
| id | int | Database primary key |
| username | str | Unique login name (immutable) |
| password_hash | str | bcrypt hash — never stored as plain text |
| role | UserRole | ADMIN / LEARNER / ANALYST / INSTRUCTOR |
| created_at | datetime | UTC account creation time |
| is_active | bool | Whether the account can log in |
| account_status | AccountStatus | ACTIVE / PENDING / REJECTED / INACTIVE |
| rejection_reason | str | Admin's reason for rejection |
| full_name | str | Display name (editable) |
| email | str | Contact email (editable) |
| bio | str | About-me description (editable) |
| preferred_difficulty | DifficultyLevel | Learner's difficulty preference |
| profile_updated_at | datetime | Last profile modification time |

Key methods:
- `validate()` — enforces business rules
- `to_dict()` — serializes for API/storage (excludes password_hash)
- `from_dict()` — reconstructs from database row (handles enum conversion)

### 7.4 Course Model (core/course.py)

Represents a learning course in the catalogue.

| Attribute | Type | Description |
|-----------|------|-------------|
| code | str | Primary key (e.g. "CS101") |
| name | str | Human-readable title |
| description | str | Detailed description |
| difficulty | DifficultyLevel | BEGINNER / INTERMEDIATE / ADVANCED |
| duration | int | Hours to complete (must be > 0) |
| status | CourseStatus | DRAFT / PUBLISHED / ARCHIVED |
| prerequisites | set[str] | Course codes that must be completed first |

**UML design decisions:**
- `prerequisites` is a **set** (not list) — prevents duplicates by data structure
- `duration` is an **int** (not float) — no fractional hours
- Self-referencing prerequisite association models the dependency graph

Key methods:
- `add_prerequisite(code)` — adds to the set (idempotent)
- `remove_prerequisite(code)` — safe even if not present (set.discard)
- `has_prerequisite(code)` → bool
- `get_prerequisites()` → set copy (external code cannot mutate internal state)

### 7.5 Learner Model (core/learner.py)

Represents a student's learning profile.

| Attribute | Type | Description |
|-----------|------|-------------|
| id | int | Database primary key |
| user_id | int | FK to Users table |
| name | str | Full display name |
| email | str | Contact email (unique) |
| completed_courses | set[str] | Derived from ENROLLMENTS (status=COMPLETED) |
| current_courses | set[str] | Derived from ENROLLMENTS (status=ENROLLED/IN_PROGRESS) |

**Design decision:** `completed_courses` and `current_courses` are NOT stored in the
LEARNERS table. They are derived from the ENROLLMENTS table every time a Learner
is loaded. This ensures a single source of truth.

### 7.6 Enrollment Model (core/enrollment.py)

Records one learner's participation in one course.

**State Machine:**

```
            ┌──────────┐
            │ ENROLLED │
            └────┬─────┘
                 │ start()
            ┌────▼──────────┐
            │  IN_PROGRESS  │
            └───┬───────┬───┘
                │       │
           complete() cancel()
                │       │
            ┌───▼───┐ ┌─▼────────┐
            │COMPLETED│ │CANCELLED │
            └────────┘ └──────────┘
```

- `ENROLLED → IN_PROGRESS`: Learner begins working on content
- `IN_PROGRESS → COMPLETED`: Learner finishes with a score (0–100)
- `ENROLLED/IN_PROGRESS → CANCELLED`: Learner drops the course
- `COMPLETED` and `CANCELLED` are **terminal states** — no further transitions

### 7.7 CourseProgress Model (core/course_progress.py)

Fine-grained progress tracking (percentage + completion status).

| Attribute | Type | Description |
|-----------|------|-------------|
| percentage | float | 0.0 – 100.0 |
| completion_status | CompletionStatus | Auto-adjusted based on percentage |

Auto-adjustment rules:
- `0%` → NOT_STARTED
- `1% – 99%` → IN_PROGRESS
- `100%` → COMPLETED
- Manual override: `mark_failed()` → FAILED

### 7.8 PriorLearningRequest Model (core/prior_learning_request.py)

Represents a learner's request to have external learning recognized.

Statuses: `PENDING → INSTRUCTOR_REVIEWED → APPROVED / REJECTED / INFO_REQUESTED`

Pathways:
- `TRANSFER` — credit from another institution
- `ASSESSMENT` — passed an external assessment
- `EXEMPTION` — significant work/life experience

### 7.9 Notification Model (core/notification.py)

System notifications for users (PLR decisions, account approvals, etc.).

Types: `INFO`, `SUCCESS`, `WARNING`, `ERROR`

---

## 8. Authentication System

### 8.1 Password Manager (auth/password_manager.py)

**Class-based** implementation (matches UML class diagram) using bcrypt.

```python
pm = PasswordManager()
hashed = pm.hash_password("admin123")      # → "$2b$12$..."
pm.verify_password("admin123", hashed)     # → True
pm.verify_password("wrong", hashed)        # → False
```

- Every call to `hash_password()` produces a different hash (unique salt)
- `verify_password()` uses constant-time comparison (prevents timing attacks)
- Empty inputs always return `False` (never crash)

### 8.2 Session Manager (auth/session_manager.py)

**Singleton pattern** — exactly one instance exists application-wide.

```python
s1 = SessionManager()
s2 = SessionManager()
print(s1 is s2)  # → True (same object)
```

Methods:
- `login(user)` — records the active user
- `logout()` — clears the session
- `current_user()` → User or None
- `is_authenticated()` → bool

### 8.3 Auth Service (auth/auth_service.py)

Business logic for authentication with account status checks.

**Login flow:**

```
User enters credentials
         ↓
Find user by username
    ├── Not found → "Invalid username or password"
    ├── PENDING   → "Your account is pending admin approval"
    ├── REJECTED  → "Your registration was rejected. Reason: ..."
    ├── INACTIVE  → "Your account has been deactivated"
    └── Found + Active
         ↓
Verify bcrypt password
    ├── Wrong → "Invalid username or password"
    └── Correct → Create session → Login successful
```

**Registration types:**
- `register()` — admin-created accounts (ACTIVE immediately)
- `register_learner()` — self-registration (PENDING, requires admin approval)

**Password change:**
- Verifies old password first
- New password minimum 8 characters
- Updates hash in database

---

## 9. Repository Layer

### 9.1 Database Class (repository/database.py)

Core infrastructure providing:
- **Connection per operation** — safe for concurrent users
- **Transaction context manager** — atomic operations with rollback on failure
- **Schema migrations** — versioned, additive, safe to re-run
- **WAL journal mode** — concurrent readers with one writer

```python
db = Database()          # uses data/lmpts.db
db = Database(path)      # custom path
db.initialize()          # creates all tables + runs migrations

with db.transaction() as conn:
    conn.execute("INSERT INTO ...")
    conn.execute("UPDATE ...")
# auto-committed on success, auto-rolled back on exception
```

### 9.2 User Repository (repository/user_repo.py)

SQLite + InMemory implementations of the user data access interface.

Key methods:
- `create_user()` — converts all enums to strings for SQLite binding
- `get_user()`, `find_by_username()` — always go through `_row_to_user()` for enum conversion
- `update_account_status()` — accepts both AccountStatus enum and string
- `update_profile()` — saves bio, preferred_difficulty, profile_updated_at
- `get_pending_users()` — returns users with PENDING account status
- `count_pending()` — badge counter for admin sidebar

### 9.3 Course Repository (repository/course_repo.py)

Prerequisites stored in **junction table** (not JSON inside courses table).

```sql
PREREQUISITES (id, course_code, prerequisite_code)
-- UNIQUE(course_code, prerequisite_code) prevents duplicates
-- ON DELETE CASCADE auto-cleans when course is deleted
```

When loading a course, prerequisites are fetched via a separate query and returned
as a Python `set` (matching the UML specification).

### 9.4 Learner Repository (repository/learner_repo.py)

**Design decision:** completed_courses and current_courses are derived from
ENROLLMENTS, not stored in LEARNERS.

```sql
-- completed = SELECT course_code FROM enrollments
--             WHERE learner_id=? AND status='COMPLETED'
-- current   = SELECT course_code FROM enrollments
--             WHERE learner_id=? AND status IN ('ENROLLED','IN_PROGRESS')
```

### 9.5 Enrollment Repository (repository/enrollment_repo.py)

Includes both `SQLiteEnrollmentRepository` and `SQLiteProgressRepository`.

The `UNIQUE(learner_id, course_code)` constraint prevents duplicate enrollment
at the database level (defense in depth — service layer also checks).

---

## 10. Algorithm Engine

### 10.1 CourseGraph (algorithms/graph.py)

Directed graph data structure with **two internal representations**:

```python
graph.graph          # forward:  prerequisite → set of dependents
graph.reverse_graph  # reverse:  course → set of its prerequisites
```

Example:
```
CS101 → CS201 → CS301

graph:         CS101 → {CS201}, CS201 → {CS301}
reverse_graph: CS201 → {CS101}, CS301 → {CS201}
```

**Why two graphs?**
- Forward graph: used by BFS path finder, topological sort
- Reverse graph: used by prerequisite validator, enrollment checks
- Both updated atomically on every `add_edge()` / `remove_edge()` call

Key methods:
- `add_edge(prerequisite, dependent)` — updates both graphs
- `get_prerequisites(course)` → set of direct prerequisites
- `get_all_prerequisites(course)` → set of ALL transitive prerequisites (BFS)
- `get_all_dependents(course)` → set of ALL courses unlocked by completing this
- `build_from_courses(codes, prereqs)` — constructs graph from database data

### 10.2 Cycle Detection (algorithms/cycle_detection.py)

Uses **Depth-First Search (DFS)** with a recursion stack.

```
Algorithm:
    For each unvisited node:
        Run DFS, tracking visited set + recursion stack
        If we reach a node already in the recursion stack
            → back edge found → CYCLE EXISTS
        Otherwise, remove from recursion stack and continue
```

Key methods:
- `detect_cycle()` → bool
- `find_cycle_path()` → list of courses forming the cycle, or None
- `would_create_cycle(prereq, dependent)` → checks WITHOUT modifying the graph
- `get_all_cycles()` → list of all distinct cycles

**Critical usage:** Called BEFORE saving any new prerequisite relationship.
If `would_create_cycle()` returns True, the operation is rejected with
`CircularDependencyError`.

### 10.3 Path Finder (algorithms/path_finder.py)

Uses **Breadth-First Search (BFS)** for shortest paths.

```
Algorithm:
    Queue = [(start, [start])]
    While queue not empty:
        current, path = dequeue
        If current == end: return path
        For each neighbor:
            If not visited: enqueue (neighbor, path + [neighbor])
    Return None (no path found)
```

Key methods:
- `find_learning_path(start, end)` → shortest path or None
- `find_all_prerequisites(course)` → all prereqs in valid study order
- `get_recommended_path(target, completed, transfers, exemptions)` → remaining courses needed
- `get_study_order(courses)` → topological order of a subset

### 10.4 Topological Sort (algorithms/topological_sort.py)

Uses **Kahn's Algorithm** (BFS-based, iterative).

```
Algorithm:
    1. Calculate in-degree for every node
    2. Add all in-degree=0 nodes to queue (alphabetical for determinism)
    3. While queue not empty:
       a. Dequeue node → add to result
       b. For each dependent: decrement in-degree
       c. If in-degree reaches 0: add to queue
    4. If result.length < total nodes → CYCLE detected
```

Key methods:
- `sort()` → all courses in valid study order (raises ValueError on cycle)
- `sort_subset(courses)` → subset in topological order
- `get_levels()` → list of lists (parallel study levels)
- `get_course_level(code)` → depth/level of a specific course

### 10.5 Prerequisite Validator (algorithms/prerequisite_validator.py)

Determines whether a learner can enroll in a course considering all credit types.

```
Validation formula:
    can_enroll = required_prerequisites ⊆ satisfied_credits

    where:
    satisfied_credits = completed ∪ transfer ∪ exemptions ∪ placement
```

**LearnerCredits** dataclass:
```python
credits = LearnerCredits(
    completed        = {"CS101", "CS102"},      # normal completion
    transfer_credits = {"MATH101"},              # from another institution
    exemptions       = {"COMM101"},              # admin-approved
    placement_tests  = {"PHYS101"},              # via placement exam
)
credits.all_satisfied  # → {"CS101", "CS102", "MATH101", "COMM101", "PHYS101"}
```

**ValidationResult** dataclass:
```python
result = validator.can_enroll(credits, "CS201")
result.can_enroll            # bool
result.missing_prerequisites # list[str]
result.satisfied_by          # dict: {course → CreditType}
result.message               # human-readable explanation
bool(result)                 # same as result.can_enroll
```

### 10.6 Recommendation Engine (algorithms/recommendation.py)

Multi-factor scoring system for course recommendations.

**Scoring formula:**
```
score = (
    prerequisite_score   (40%)  +   # all prereqs met = higher
    difficulty_match     (30%)  +   # matches learner preference
    path_length_score    (20%)  +   # shorter remaining path = higher
    duration_score       (10%)      # shorter course = higher
)
```

Each recommendation includes:
- `course_code`, `course_name`
- `score` (0–100)
- `reasons` (list of human-readable justifications)
- `remaining` (courses unlocked by completing this)

---

## 11. Service Layer

### 11.1 CourseService

Orchestrates course lifecycle management.

| Method | Description |
|--------|-------------|
| `create_course(course)` | Save + add to graph |
| `update_course(course)` | Update + rebuild graph |
| `delete_course(code)` | Delete + remove from graph (cascades) |
| `publish_course(code)` | DRAFT → PUBLISHED |
| `archive_course(code)` | PUBLISHED → ARCHIVED |
| `add_prerequisite(course, prereq)` | **With cycle detection** |
| `remove_prerequisite(course, prereq)` | Remove + update graph |
| `get_study_order()` | Topological sort |
| `get_course_levels()` | Parallel study levels |

### 11.2 EnrollmentService

Orchestrates enrollment with prerequisite validation.

| Method | Description |
|--------|-------------|
| `enroll_learner(learner_id, code)` | Validate prereqs → create enrollment + progress (atomic) |
| `start_enrollment(learner_id, code)` | ENROLLED → IN_PROGRESS |
| `complete_enrollment(learner_id, code, score)` | Set COMPLETED + score + update progress (atomic) |
| `cancel_enrollment(learner_id, code)` | Set CANCELLED |
| `transfer_credit(learner_id, code)` | Admin: mark as COMPLETED (transfer) |
| `approve_exemption(learner_id, code)` | Admin: mark as exempt |

**EnrollmentResult** (soft validation failures):
```python
result = service.enroll_learner(learner_id, "CS301")
result.success                # bool
result.enrollment             # Enrollment object (if success)
result.missing_prerequisites  # list[str] (if failed)
result.message                # explanation
```

### 11.3 ProgressService

Tracks learner progress with auto-adjusting status.

| Method | Description |
|--------|-------------|
| `update_progress(learner_id, code, percentage)` | Auto-adjusts CompletionStatus |
| `mark_failed(learner_id, code)` | Sets FAILED status |
| `calculate_completion_rate(learner_id)` | completed / total enrolled × 100 |
| `get_learning_path_progress(learner_id, goal)` | Progress toward a specific goal |
| `get_overall_summary(learner_id)` | Counts by status + completion rate |

### 11.4 AnalyticsService

Aggregate reports for admin and analyst dashboards.

| Method | Description |
|--------|-------------|
| `course_completion_rate(code)` | Enrolled, completed, cancelled, rates |
| `most_enrolled_courses(limit)` | Ranked by enrollment count |
| `bottleneck_courses(threshold)` | High dropout rate courses |
| `average_score_by_course()` | Mean score for completed learners |
| `difficulty_distribution()` | Count per difficulty level |
| `prerequisite_chain_length()` | Depth analysis for every course |
| `learner_progress_summary(id)` | Per-learner detailed report |
| `learner_activity_report()` | All learners ranked by completion rate |
| `system_overview()` | Global statistics dashboard |

### 11.5 LearningPathService

Generates personalized learning paths.

| Method | Description |
|--------|-------------|
| `get_path_to_course(start, end)` | BFS shortest path |
| `get_learner_roadmap(id, goal)` | Personalized roadmap with progress |
| `get_available_next_courses(id)` | Courses the learner can enroll now |
| `get_full_curriculum_order()` | Complete topological order |
| `get_curriculum_levels()` | Parallel study levels |
| `get_prerequisites_for(code)` | Ordered prerequisite chain |

### 11.6 RecommendationService

Bridges the algorithm engine with database data.

| Method | Description |
|--------|-------------|
| `get_recommendations(id, difficulty, limit, goals)` | Ranked recommendations |
| `get_learning_roadmap(id, goals)` | Multi-goal roadmap |

### 11.7 PriorLearningService

Manages the full transfer credit workflow.

| Method | Description |
|--------|-------------|
| `submit_request(...)` | Learner submits PLR |
| `instructor_review(id, recommendation, note)` | Instructor recommends |
| `admin_decision(id, decision, note)` | Admin approves/rejects (auto-applies credit) |
| `get_learner_requests(id)` | Learner's request history |
| `get_pending_instructor_review()` | Queue for instructors |
| `get_pending_admin_decision()` | Queue for admins |

### 11.8 AccountService

Manages registration approval workflow.

| Method | Description |
|--------|-------------|
| `get_pending_registrations()` | All PENDING accounts |
| `approve_registration(id, admin_id, note)` | Activate + create learner profile + notify |
| `reject_registration(id, admin_id, reason)` | Reject + store reason + notify |
| `request_more_information(id, admin_id, msg)` | Keep PENDING + notify |
| `deactivate_user(id, admin_id, reason)` | Suspend account |
| `reactivate_user(id, admin_id)` | Restore account |

### 11.9 ProfileService

Manages user profile updates with validation.

| Method | Description |
|--------|-------------|
| `get_profile(user_id)` | Fetch full profile |
| `update_personal_info(id, name, email, bio, difficulty)` | Save + sync learner + notify if email changed |
| `change_password(id, old_pw, new_pw)` | Verify old + validate new + notify + force logout |
| `calculate_password_strength(password)` | Score 0-100 with issues list |

**Password complexity rules:**
- Minimum 8 characters
- At least one uppercase letter
- At least one digit
- Must differ from current password

---

## 12. GUI Application

### 12.1 Login Window

Professional dark-blue themed login screen.

Features:
- Username and password fields
- "Remember me" checkbox
- Error messages for wrong credentials
- **Specific messages for PENDING and REJECTED accounts**
- "New to LMPTS? Create Account" link → opens registration window

### 12.2 Self-Registration Window

Full registration form for new learners.

Fields:
- Full Name
- Email Address
- Username (3–20 characters, alphanumeric + underscore)
- Password (with live strength meter)
- Confirm Password

After submission:
- Account created with PENDING status
- Success screen: "Account Pending Approval"
- Admin notified via notification system
- Learner cannot log in until admin approves

### 12.3 Main Window (Sidebar Layout)

```
┌──────────────────────────────────────────────────┐
│  LMPTS    Learning Management System    👤 admin │
├───────────┬──────────────────────────────────────┤
│           │                                      │
│  Sidebar  │          Content Area                │
│           │                                      │
│  Nav      │    (screens load here based on       │
│  Items    │     which sidebar item is clicked)   │
│           │                                      │
│  [Logout] │                                      │
└───────────┴──────────────────────────────────────┘
```

**Sidebar features:**
- Hover effect (lighter blue)
- Active/selected state (bright blue)
- Role-specific navigation items
- Logout button at bottom
- Clicking username in header opens profile

### 12.4 Admin Dashboard

Overview statistics:
- Total Courses / Learners / Enrollments / Completion Rate
- Recent enrollments table
- Quick action buttons
- Difficulty distribution bar

### 12.5 Admin Screens

| Screen | Features |
|--------|----------|
| **Pending Registrations** | Approve/reject/request-info, detail panel, badge count |
| **Course Management** | CRUD, filters, publish/archive, form dialog |
| **Course Approvals** | Review instructor submissions, approve/reject |
| **Prerequisite Management** | Canvas graph + text view, add/remove prereqs |
| **Learner Management** | View all, transfer credits, exemptions, delete |
| **User Management** | Create/delete accounts, change passwords |
| **Prior Learning Approval** | Final PLR decisions with auto-credit application |
| **Analytics** | System overview, course stats, learner activity, charts |

### 12.6 Learner Dashboard

Progress overview:
- Enrolled / Completed / In Progress / Available course counts
- Overall completion rate with progress bar
- Active courses list
- Available courses with enroll button

### 12.7 Learner Screens

| Screen | Features |
|--------|----------|
| **My Courses** | Filter by status, start/complete/cancel enrollments |
| **Learning Path** | Goal selector, roadmap text, canvas graph with highlights |
| **Progress** | Per-course progress bars with completion status |
| **Prior Learning** | Submit requests, track status, view notes |
| **Recommendations** | Scored cards with reasons, difficulty filter, enroll button |

### 12.8 Instructor Dashboard

Statistics + notification panel + quick actions.

### 12.9 Instructor Screens

| Screen | Features |
|--------|----------|
| **My Courses** | Create DRAFT courses, edit, submit for admin review |
| **Monitor Learners** | Three-pane: learners → courses → actions |
| **Prior Learning Review** | Review evidence, recommend approve/reject/info |

### 12.10 Analyst Screens

| Screen | Features |
|--------|----------|
| **Analytics Reports** | Full completion rates table for all courses |
| **Completion Stats** | Prerequisite chain length analysis |
| **Bottleneck Analysis** | Configurable dropout threshold, flagged courses |

### 12.11 Profile Screen (All Roles)

Three tabs:
1. **Personal Information** — edit name, email, bio, difficulty preference
2. **Change Password** — with strength meter and complexity requirements
3. **Account Details** — read-only system info

### 12.12 Reusable Widgets

| Widget | File | Purpose |
|--------|------|---------|
| `Sidebar` | widgets/sidebar.py | Navigation with hover/selected states |
| `CourseTable` | widgets/course_table.py | Sortable ttk.Treeview for courses |
| `GraphView` | widgets/graph_view.py | Canvas prerequisite diagram |
| `PasswordStrengthMeter` | widgets/password_strength.py | Live strength meter |
| `confirm()` | dialogs/confirm_dialog.py | Yes/No confirmation dialog |
| `show_error()` | dialogs/confirm_dialog.py | Error message dialog |
| `show_info()` | dialogs/confirm_dialog.py | Information message dialog |

---

## 13. User Roles and Responsibilities

### 13.1 Administrator

Full system control.

- Manage user accounts (create, activate, deactivate, delete)
- Approve or reject learner registrations
- Create, edit, publish, archive, and delete courses
- Approve or reject courses submitted by instructors
- Manage course prerequisites with cycle detection
- Override prerequisite restrictions when necessary
- Make final decisions on prior learning requests
- Grant course exemptions for approved prior learning
- View and manage all learner enrollments
- Access system-wide analytics
- Configure default system accounts

### 13.2 Instructor

Course creation and learner oversight.

- Create new courses (saved as DRAFT)
- Edit and update course information
- Submit courses to administrator for approval
- Monitor learner progress and performance
- Mark learner course completion with scores
- Review prior learning requests from learners
- Provide recommendations (Approve / Reject / Request Info) to admin
- View course-specific progress reports
- Receive notifications about new PLR submissions

### 13.3 Learner

Self-directed learning with guided paths.

- Register for an account (requires admin approval)
- Browse published courses
- View course details, prerequisites, and duration
- Enroll in courses with all prerequisites satisfied
- Submit prior learning requests for external credits
- Track request status (Pending / Approved / Rejected)
- View current enrollments and completed courses
- Monitor personal learning progress
- Follow recommended learning paths
- View personalized course recommendations
- Update personal profile and change password

### 13.4 Analyst

Read-only access to system data.

- View system-wide dashboards
- Monitor enrollment statistics
- Analyze course completion rates
- Identify bottleneck courses
- Analyze prerequisite dependency chains
- View difficulty distribution
- Generate learner activity reports
- View learner progression trends

**Note:** Analysts have **read-only access** and cannot modify courses,
users, enrollments, or system settings.

---

## 14. Approval Workflows

### 14.1 Learner Account Activation

```
Learner clicks "Create Account" on login screen
         ↓
Fills registration form (name, email, username, password)
         ↓
Account created with:
    is_active = False
    account_status = PENDING
         ↓
Admin notified via notification system
         ↓
Admin goes to "Pending Registrations"
         ↓
Admin reviews registration details
    ├── APPROVE → Account activated, learner profile created,
    │             learner notified, can now log in
    ├── REJECT  → Status set to REJECTED, reason stored,
    │             learner sees reason when trying to log in
    └── REQUEST INFO → Stays PENDING, notification recorded
```

### 14.2 Course Approval (Instructor → Admin)

```
Instructor creates course (status = DRAFT)
         ↓
Instructor clicks "Submit for Review"
    → course_submissions record created (PENDING)
    → Admin notified
         ↓
Admin reviews course in "Course Approvals" screen
    ├── APPROVE → Course published (PUBLISHED),
    │             instructor notified
    └── REJECT  → Course stays DRAFT, rejection reason sent,
                  instructor notified
```

### 14.3 Prior Learning / Transfer Credit

```
Learner submits request (PENDING)
    → Chooses pathway: TRANSFER / ASSESSMENT / EXEMPTION
    → Provides evidence description
    → All instructors notified
         ↓
Instructor reviews evidence
    → Recommends: APPROVE / REJECT / INFO_REQUESTED
    → Adds review notes
    → Status changes to INSTRUCTOR_REVIEWED
    → Admin notified
         ↓
Admin makes final decision
    ├── APPROVED → transfer_credit() called automatically,
    │              prerequisite satisfied, learner notified
    └── REJECTED → Learner must complete course normally,
                   learner notified with reason
```

### 14.4 Course Enrollment

```
Learner selects a published course
         ↓
System validates prerequisites:
    1. Get learner's completed courses
    2. Get learner's transfer credits
    3. Get learner's exemptions
    4. Union all = satisfied_credits
    5. Check: required_prerequisites ⊆ satisfied_credits
         ↓
    ├── All satisfied → Enrollment created + progress initialized
    │                   (both in single transaction)
    └── Missing → Show missing prerequisites,
                  recommend the required learning path
```

---

## 15. Prior Learning / Transfer Credit System

### Overview

Learners who have completed courses on other platforms (Coursera, edX,
university courses, etc.) can request to have their prior learning
recognized in LMPTS.

### Credit Types

| Type | Description | Example |
|------|-------------|---------|
| TRANSFER | Credit from another institution | "Completed CS101 at MIT" |
| ASSESSMENT | Passed an external assessment | "Scored 92% on AWS exam" |
| EXEMPTION | Significant work/life experience | "5 years as Python developer" |

### How It Works

1. **Learner submits request** in "Prior Learning" screen
   - Selects the course to be credited
   - Chooses pathway (Transfer / Assessment / Exemption)
   - Describes evidence (certificates, transcripts, experience)
   - Optionally provides platform name and external score

2. **Instructor reviews** in "Prior Learning Review" screen
   - Views evidence description
   - Provides recommendation: Approve / Reject / Request Info
   - Adds review notes for the admin

3. **Admin makes final decision** in "Prior Learning Approval" screen
   - Sees instructor's recommendation
   - Reviews full evidence
   - Approves (auto-grants transfer credit) or Rejects

4. **Learner is notified** of the decision
   - If approved: prerequisite automatically satisfied
   - If rejected: must complete the course normally

### Impact on Enrollment

After a transfer credit is approved, the learner's prerequisite check
includes the credited course. Example:

```
Before transfer credit:
    CS301 requires CS201
    Learner has: CS101 ✓, CS201 ✗
    → Cannot enroll in CS301

After transfer credit for CS201:
    satisfied_credits = {CS101, CS201}  (CS201 = TRANSFER)
    → Can now enroll in CS301
```

---

## 16. Account Activation System

### Why Account Activation?

Prevents unauthorized access. A learner must be approved by an
administrator before they can use the system.

### Account Statuses

| Status | Can Log In? | Meaning |
|--------|-------------|---------|
| ACTIVE | ✅ Yes | Approved, fully functional |
| PENDING | ❌ No | Registered, awaiting admin approval |
| REJECTED | ❌ No | Registration denied by admin |
| INACTIVE | ❌ No | Previously active, suspended by admin |

### Login Behavior by Status

| Status | Login Screen Message |
|--------|---------------------|
| ACTIVE | Normal login → opens dashboard |
| PENDING | "Your account is pending admin approval. Please wait..." |
| REJECTED | "Your registration was rejected. Reason: [admin's reason]" |
| INACTIVE | "Your account has been deactivated. Contact admin." |

### Admin Actions

| Action | Effect |
|--------|--------|
| **Approve** | is_active=True, status=ACTIVE, learner profile created, notification sent |
| **Reject** | status=REJECTED, reason stored, notification recorded |
| **Request Info** | Stays PENDING, message recorded for reference |
| **Deactivate** | is_active=False, status=INACTIVE (can be reactivated) |
| **Reactivate** | is_active=True, status=ACTIVE (from REJECTED or INACTIVE) |

---

## 17. Profile Management

### Features

Available to **all roles** (Admin, Learner, Instructor, Analyst).

**Personal Information Tab:**
- Edit full name and email (with email format validation)
- Edit bio / about-me (max 500 characters with live counter)
- Set preferred difficulty level (Learners only — used for recommendations)
- Read-only fields: username, role, member-since date

**Change Password Tab:**
- Current password verification (prevents unauthorized changes)
- New password with live strength meter
- Confirm password with match indicator
- Complexity requirements displayed
- After successful change: notification created + forced logout

**Account Details Tab:**
- Read-only view of all account information
- User ID, role, status, activity dates

### Password Strength Scoring

```
Score 0-100 based on:
    Length ≥ 8   → +25
    Length ≥ 12  → +15
    Length ≥ 16  → +10
    Has uppercase → +15
    Has lowercase → +10
    Has digit     → +15
    Has special   → +10

Labels:
    0-29   → Weak   (red)
    30-59  → Fair   (orange)
    60-79  → Good   (blue)
    80-100 → Strong (green)

Mandatory requirements:
    ✓ At least 8 characters
    ✓ At least one uppercase letter
    ✓ At least one digit
```

---

## 18. Notification System

### How Notifications Work

Notifications are stored in the database and displayed to users
in their respective dashboards.

### Events That Create Notifications

| Event | Notified Users | Type |
|-------|---------------|------|
| New learner registration | All admins | INFO |
| Registration approved | Learner | SUCCESS |
| Registration rejected | Learner | WARNING |
| PLR request submitted | All instructors | INFO |
| PLR instructor reviewed | All admins | INFO |
| PLR more info requested | Learner | WARNING |
| PLR approved by admin | Learner | SUCCESS |
| PLR rejected by admin | Learner | WARNING |
| Course submitted for review | All admins | INFO |
| Course approved | Instructor | SUCCESS |
| Course rejected | Instructor | WARNING |
| Password changed | User | SUCCESS |
| Email changed | User | INFO |
| Account deactivated | User | WARNING |
| Account reactivated | User | SUCCESS |

---

## 19. Analytics and Reporting

### System Overview (Admin Dashboard)

| Metric | Calculation |
|--------|-------------|
| Total Courses | COUNT(*) from courses |
| Total Learners | COUNT(*) from learners |
| Total Enrollments | SUM(enrolled counts across all learners) |
| Overall Completion Rate | total_completed / total_enrolled × 100 |
| Difficulty Distribution | COUNT per BEGINNER/INTERMEDIATE/ADVANCED |

### Course Analytics

| Report | Description |
|--------|-------------|
| **Completion Rate** | enrolled, completed, in_progress, cancelled, rates per course |
| **Most Enrolled** | Ranked by enrollment count (configurable limit) |
| **Bottleneck Courses** | High dropout rate above configurable threshold |
| **Average Score** | Mean score of completed learners per course |
| **Chain Length** | Number of transitive prerequisites per course |

### Learner Analytics

| Report | Description |
|--------|-------------|
| **Progress Summary** | Per-learner: enrolled, completed, in_progress, rate, avg score |
| **Activity Report** | All learners ranked by completion rate |
| **Learning Path Progress** | Percentage completion toward a specific goal |
| **Overall Summary** | Counts by CompletionStatus + completion rate |

### Charts (matplotlib)

When matplotlib is installed, the analytics dashboard shows:
- Bar chart of most enrolled courses
- Difficulty distribution progress bars

---

## 20. Testing

### Test Suite Organization

```
tests/
├── test_models.py                  # 165 tests — core models + auth
├── test_algorithms.py              # ~80 tests — all algorithm classes
├── repository/
│   └── test_sqlite_repositories.py # 113 tests — database layer
├── algorithms/
│   ├── test_graph.py
│   ├── test_cycle_detection.py
│   ├── test_topological_sort.py
│   ├── test_path_finder.py
│   ├── test_prerequisite_validator.py
│   └── test_recommendation.py
└── services/
    ├── test_course_service.py
    ├── test_enrollment_service.py
    ├── test_progress_service.py
    ├── test_analytics_service.py
    └── test_learning_path_service.py
```

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific module
python -m pytest tests/test_models.py -v

# Specific class
python -m pytest tests/test_models.py::TestUser -v

# With coverage
python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Only algorithm tests
python -m pytest tests/algorithms/ tests/test_algorithms.py -v

# Only service tests
python -m pytest tests/services/ -v

# Only repository tests
python -m pytest tests/repository/ -v
```

### Test Design

| Approach | Used For |
|----------|----------|
| **pytest fixtures** | Shared test data setup |
| **tmp_path** | Isolated temp databases per test |
| **InMemoryUserRepository** | Fast unit tests without SQLite |
| **Autouse fixtures** | SessionManager.reset() before every test |
| **Integration tests** | Full workflow with real SQLite files |

### Total Test Count

```
Person 1 (Core + Auth):    165 tests
Person 2 (Repositories):   113 tests
Person 3 (Algorithms):     ~80 tests (across 6 test files)
Person 4 (Services):       ~80 tests (across 5 test files)
                           ─────────
Total:                     ~540+ tests
```

---

## 21. Running the Application

### Standard Launch

```bash
cd C:\LMPTS
python gui/app.py
```

### Launch Specific Role (Skip Login)

```bash
python launch_role.py admin
python launch_role.py learner
python launch_role.py analyst
python launch_role.py instructor
```

### Launch All Four Roles Simultaneously

```bash
python launch_all.py
```

### Launch Multiple Login Windows

```bash
python multi_login.py       # 2 windows
python multi_login.py 4     # 4 windows
```

### Initialize Database Only

```bash
python setup_database.py
```

---

## 22. Default Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | ADMIN |
| learner | learner123 | LEARNER |
| analyst | analyst123 | ANALYST |
| instructor | instructor123 | INSTRUCTOR |

All default accounts are created with ACTIVE status.
Passwords are stored as bcrypt hashes — never in plain text.

### Sample Data

On first launch, the system seeds:
- 6 courses: CS101, CS102, CS201, CS301, ML101, PY101
- Prerequisites: CS201→CS101, CS201→CS102, CS301→CS201, ML101→CS201
- 1 learner profile linked to the default learner account
- 1 instructor account

---

## 23. UML Diagrams

### 23.1 Use Case Diagram

```
Administrator ────→ Login
              ────→ Manage Courses
              ────→ Manage Prerequisites
              ────→ Approve Registrations
              ────→ Approve Transfer Credits
              ────→ View Analytics

Learner ──────────→ Register
              ────→ Login
              ────→ Enroll in Course
              ────→ Submit PLR Request
              ────→ View Progress
              ────→ View Recommendations

Instructor ───────→ Login
              ────→ Create Course
              ────→ Monitor Learners
              ────→ Review PLR Requests

Analyst ──────────→ Login
              ────→ Generate Reports
              ────→ Analyze Statistics
```

### 23.2 Class Diagram (Core)

```
┌──────────────┐       ┌──────────────┐
│     User     │       │   Learner    │
├──────────────┤       ├──────────────┤
│ username     │──────→│ user_id  FK  │
│ role         │       │ name         │
│ account_status│      │ completed    │
│ full_name    │       │ current      │
└──────────────┘       └──────────────┘
                              │
                              │ 1..* 
                              ▼
┌──────────────┐       ┌──────────────┐
│   Course     │──────→│ Enrollment   │
├──────────────┤       ├──────────────┤
│ code  PK     │       │ learner_id   │
│ prerequisites│←─┐    │ course_code  │
│ difficulty   │  │    │ status       │
│ status       │  │    │ score        │
└──────────────┘  │    └──────────────┘
      │           │
      └───────────┘ (self-association)
```

### 23.3 Enrollment State Diagram

```
[*] → ENROLLED → IN_PROGRESS → COMPLETED
                             → CANCELLED
      ENROLLED → CANCELLED
```

### 23.4 Prerequisite Graph Example

```
CS101 ──→ CS201 ──→ CS301
CS102 ──→ CS201
CS201 ──→ ML101

Invalid (cycle): CS101 → CS201 → CS301 → CS101
                 ↑ Detected by DFS → CircularDependencyError
```

---

## 24. Future Enhancements

### Priority 1 — Specification Completions

| Feature | Description |
|---------|-------------|
| Course Search & Filter | Search by name, filter by difficulty/status |
| CSV/PDF Export | Export analytics tables for analyst |
| Notification Bell | Badge count in header, notification panel |

### Priority 2 — Quality Improvements

| Feature | Description |
|---------|-------------|
| Auto-refresh | Dashboard data refreshes every 30 seconds |
| Better Error Messages | Human-readable with action suggestions |
| Loading Indicators | Threading for slow database operations |
| Input Validation | Red borders on invalid fields, inline hints |

### Priority 3 — New Features

| Feature | Description |
|---------|-------------|
| Web Interface (Flask) | Browser-based access for multiple users |
| Certificate Generation | PDF certificates for completed courses |
| Quiz/Assessment System | In-app quizzes for placement and completion |
| Course Categories | Group courses into departments |
| Learning Streak | Track consecutive days of activity |
| Deadline Tracking | Enrollment/completion deadlines with warnings |
| Audit Log | Record every action with who/when |
| Dark Mode | Theme toggle for the interface |
| Email Notifications | Real email delivery for PLR decisions |
| Database Backup | Admin-triggered backup with restore |

### Priority 4 — Technical Improvements

| Feature | Description |
|---------|-------------|
| PostgreSQL Support | Swap SQLite for production database |
| REST API (Flask/FastAPI) | Enable mobile/web client access |
| Docker Deployment | Containerized deployment |
| CI/CD Pipeline | Automated testing on push |
| Logging | Structured logging to file with rotation |
| Configuration File | External settings (DB path, theme, etc.) |

---

## License

This project is an academic/educational project developed as a semester
project for demonstrating software engineering practices including:

- Layered architecture
- Repository pattern
- Design patterns (Singleton, Factory, Strategy)
- Graph algorithms (DFS, BFS, Topological Sort)
- Test-driven development
- Database migration management
- Role-based access control
- Approval workflows

---

## Contributors

| Person | Responsibility | Percentage |
|--------|---------------|------------|
| Person 1 | Core Models + Authentication | 25-30% |
| Person 2 | Database + Repository Layer | 20% |
| Person 3 | Algorithm Engine | 15% |
| Person 4 | Service Layer | 20% |
| Person 5 | GUI Application | 20% |

---

*Last updated: July 2026*
*Schema version: v4*
*Total tests: 540+*
```
