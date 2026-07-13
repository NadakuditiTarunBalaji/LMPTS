# LMPTS — Database Design

This document covers the complete database schema, design decisions,
migration history, indexing strategy, and query patterns for LMPTS.

**Database:** SQLite 3 with WAL journal mode
**File:** `data/lmpts.db`
**Schema version:** v4
**Managed by:** `repository/database.py`

---

## Table of Contents

1. [Design Decisions](#1-design-decisions)
2. [Entity Relationship Diagram](#2-entity-relationship-diagram)
3. [Table Definitions](#3-table-definitions)
4. [Schema Migrations](#4-schema-migrations)
5. [Indexes](#5-indexes)
6. [Key Query Patterns](#6-key-query-patterns)
7. [Connection Management](#7-connection-management)
8. [Integrity Rules](#8-integrity-rules)
9. [Seed Data](#9-seed-data)

---

## 1. Design Decisions

| Decision | Rationale |
|----------|-----------|
| **SQLite with WAL mode** | WAL (Write-Ahead Log) allows multiple concurrent readers with one writer — safe for simultaneous desktop + web access to the same file |
| **Connection-per-operation** | Each database call opens, uses, and closes its own connection. Prevents long-lived connection issues in a multi-user scenario |
| **Prerequisites in junction table** | `PREREQUISITES(course_code, prerequisite_code)` is a proper relational many-to-many design. Avoids JSON columns, makes graph queries simple SQL joins |
| **`completed_courses` derived from enrollments** | The `LEARNERS` table has no `completed_courses` column. It is derived every time via `SELECT course_code FROM enrollments WHERE status='COMPLETED'`. Single source of truth — no duplication |
| **`ON DELETE CASCADE`** | Deleting a user cascades to their learner record, enrollments, and progress. Deleting a course cascades to prerequisites and enrollments. Referential integrity enforced automatically |
| **Unique constraint on enrollments** | `UNIQUE(learner_id, course_code)` at the database level prevents duplicate enrollment even if the service layer check is bypassed |
| **Temp file databases for tests** | Tests use `pytest`'s `tmp_path` fixture to create a real SQLite file in a temp directory. This avoids the shared-cache problems of `:memory:` databases and gives each test full isolation |
| **Schema version table** | `SCHEMA_VERSION` tracks which migrations have been applied. Migrations are safe to re-run — they check the current version before executing |
| **Atomic enrollment** | Creating an enrollment and its progress record happens inside a single `with db.transaction()` block. Both succeed or both roll back |

---

## 2. Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          USERS                                   │
│                                                                   │
│  id PK · username UNIQUE · password_hash · role                  │
│  is_active · account_status · rejection_reason                   │
│  full_name · email · bio · preferred_difficulty                  │
│  profile_updated_at · created_at                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │ 1
                       │
                       │ has one
                       │
                       ▼ 0..1
┌──────────────────────────────────────────────────────────────────┐
│                         LEARNERS                                  │
│                                                                   │
│  id PK · user_id FK → USERS(id) · name · email UNIQUE           │
└──────────┬───────────────────────────────────────────────────────┘
           │ 1
           │
           │ has many
           │
           ▼ 0..*
┌──────────────────────┐          ┌────────────────────────────────┐
│      ENROLLMENTS      │          │           COURSES              │
│                       │          │                                │
│  id PK                │          │  code PK                       │
│  learner_id FK        │◄────────►│  name                          │
│  course_code FK       │  many    │  description                   │
│  status               │  to many │  difficulty                    │
│  score                │          │  duration                      │
│  enrolled_at          │          │  status                        │
│  completed_at         │          └───────────┬────────────────────┘
│  UNIQUE(learner,      │                      │
│         course)       │                      │ self-referencing
└──────────┬────────────┘                      │ many-to-many
           │ 1                                 │
           │                                   ▼
           │ has one         ┌────────────────────────────────────┐
           │                 │         PREREQUISITES              │
           ▼ 0..1            │                                    │
┌──────────────────────┐     │  id PK                             │
│   COURSE_PROGRESS    │     │  course_code FK → COURSES          │
│                       │     │  prerequisite_code FK → COURSES   │
│  id PK                │     │  UNIQUE(course_code,              │
│  learner_id FK        │     │          prerequisite_code)       │
│  course_code FK       │     └────────────────────────────────────┘
│  percentage           │
│  completion_status    │     ┌────────────────────────────────────┐
│  updated_at           │     │    CANCELLATION_REQUESTS           │
│  UNIQUE(learner,      │     │                                    │
│         course)       │     │  id PK                             │
└───────────────────────┘     │  enrollment_id FK → ENROLLMENTS   │
                              │  learner_id FK → LEARNERS          │
┌──────────────────────────┐  │  course_code FK → COURSES          │
│  PRIOR_LEARNING_REQUESTS │  │  reason                            │
│                           │  │  status                            │
│  id PK                    │  │  submitted_at                      │
│  learner_id FK            │  └────────────────────────────────────┘
│  course_code FK           │
│  pathway                  │  ┌────────────────────────────────────┐
│  evidence_description     │  │       COURSE_SUBMISSIONS           │
│  external_platform        │  │                                    │
│  external_score           │  │  id PK                             │
│  status                   │  │  course_code FK → COURSES          │
│  instructor_recommendation│  │  instructor_id FK → USERS          │
│  instructor_note          │  │  status                            │
│  instructor_id FK         │  │  instructor_note                   │
│  admin_note               │  │  admin_note                        │
│  admin_id FK              │  │  submitted_at                      │
│  submitted_at             │  │  decided_at                        │
│  reviewed_by_instructor_at│  └────────────────────────────────────┘
│  decided_by_admin_at      │
└───────────────────────────┘  ┌────────────────────────────────────┐
                               │          NOTIFICATIONS              │
┌──────────────────────────┐   │                                    │
│      SCHEMA_VERSION       │   │  id PK                             │
│                           │   │  user_id FK → USERS               │
│  version PK               │   │  message                           │
│  applied_at               │   │  notification_type                 │
└───────────────────────────┘   │  is_read                           │
                                │  created_at                        │
                                └────────────────────────────────────┘
```

---

## 3. Table Definitions

### USERS

```sql
CREATE TABLE IF NOT EXISTS users (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    username         TEXT    NOT NULL UNIQUE,
    password_hash    TEXT    NOT NULL,
    role             TEXT    NOT NULL,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),

    -- v3 columns: account activation
    is_active        INTEGER NOT NULL DEFAULT 1,
    account_status   TEXT    NOT NULL DEFAULT 'ACTIVE',
    rejection_reason TEXT,
    full_name        TEXT    NOT NULL DEFAULT '',
    email            TEXT    NOT NULL DEFAULT '',

    -- v4 columns: profile management
    bio                   TEXT    DEFAULT '',
    preferred_difficulty  TEXT    DEFAULT NULL,
    profile_updated_at    TEXT    DEFAULT NULL
);
```

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-incremented |
| `username` | TEXT UNIQUE | 3–20 chars, alphanumeric + underscore |
| `password_hash` | TEXT | bcrypt hash — never plain text |
| `role` | TEXT | `ADMIN`, `LEARNER`, `INSTRUCTOR`, `ANALYST` |
| `is_active` | INTEGER | `1` = can log in, `0` = blocked |
| `account_status` | TEXT | `ACTIVE`, `PENDING`, `REJECTED`, `INACTIVE` |
| `rejection_reason` | TEXT | Nullable — set on rejection |
| `preferred_difficulty` | TEXT | Nullable — learner recommendation filter |
| `profile_updated_at` | TEXT | ISO datetime string |

---

### LEARNERS

```sql
CREATE TABLE IF NOT EXISTS learners (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name     TEXT    NOT NULL,
    email    TEXT    NOT NULL UNIQUE
);
```

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | FK → USERS | `UNIQUE` — one learner profile per user |
| `name` | TEXT | Synced from `users.full_name` on profile update |
| `email` | TEXT UNIQUE | Synced from `users.email` on profile update |

> **No `completed_courses` or `current_courses` columns.**
> These are derived at query time from the `ENROLLMENTS` table.

---

### COURSES

```sql
CREATE TABLE IF NOT EXISTS courses (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    difficulty  TEXT NOT NULL,
    duration    INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'DRAFT'
);
```

| Column | Type | Notes |
|--------|------|-------|
| `code` | TEXT PK | Human-readable, e.g. "CS101" |
| `difficulty` | TEXT | `BEGINNER`, `INTERMEDIATE`, `ADVANCED` |
| `duration` | INTEGER | Hours, must be > 0 |
| `status` | TEXT | `DRAFT`, `PUBLISHED`, `ARCHIVED` |

---

### PREREQUISITES

```sql
CREATE TABLE IF NOT EXISTS prerequisites (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code       TEXT NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    prerequisite_code TEXT NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    UNIQUE(course_code, prerequisite_code)
);
```

| Column | Type | Notes |
|--------|------|-------|
| `course_code` | FK | The course that has the requirement |
| `prerequisite_code` | FK | The course that must be completed first |
| `UNIQUE(course_code, prerequisite_code)` | Constraint | Prevents duplicate edges |
| `ON DELETE CASCADE` | Behaviour | If either course is deleted, the edge is automatically removed |

**Reading the relationship:**
```
Row: (course_code="CS201", prerequisite_code="CS101")
Meaning: "To take CS201, you must first complete CS101"
```

---

### ENROLLMENTS

```sql
CREATE TABLE IF NOT EXISTS enrollments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id   INTEGER NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
    course_code  TEXT    NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    status       TEXT    NOT NULL DEFAULT 'ENROLLED',
    score        REAL,
    enrolled_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    UNIQUE(learner_id, course_code)
);
```

| Column | Type | Notes |
|--------|------|-------|
| `status` | TEXT | `ENROLLED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` |
| `score` | REAL | Nullable — set only on `COMPLETED` |
| `UNIQUE(learner_id, course_code)` | Constraint | One enrollment record per learner/course pair ever |

**State machine:**
```
ENROLLED → IN_PROGRESS → COMPLETED
ENROLLED → CANCELLED
IN_PROGRESS → CANCELLED
COMPLETED and CANCELLED are terminal — no further transitions
```

---

### COURSE_PROGRESS

```sql
CREATE TABLE IF NOT EXISTS course_progress (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id        INTEGER NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
    course_code       TEXT    NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    percentage        REAL    NOT NULL DEFAULT 0.0,
    completion_status TEXT    NOT NULL DEFAULT 'NOT_STARTED',
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(learner_id, course_code)
);
```

| Column | Type | Notes |
|--------|------|-------|
| `percentage` | REAL | 0.0–100.0 |
| `completion_status` | TEXT | `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `FAILED` |

**Auto-adjustment by ProgressService:**
```
percentage == 0.0         → NOT_STARTED
0.0 < percentage < 100.0  → IN_PROGRESS
percentage == 100.0        → COMPLETED
manual override            → FAILED (terminal)
```

---

### CANCELLATION_REQUESTS

```sql
CREATE TABLE IF NOT EXISTS cancellation_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    learner_id    INTEGER NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
    course_code   TEXT    NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    reason        TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'PENDING',
    submitted_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

| Column | Type | Notes |
|--------|------|-------|
| `status` | TEXT | `PENDING`, `APPROVED`, `REJECTED`, `WITHDRAWN` |
| `reason` | TEXT | Learner's explanation — required |

**Only `ENROLLED` (not started) enrollments can have a cancellation request.**

---

### PRIOR_LEARNING_REQUESTS

```sql
CREATE TABLE IF NOT EXISTS prior_learning_requests (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id                  INTEGER NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
    course_code                 TEXT    NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    pathway                     TEXT    NOT NULL,
    evidence_description        TEXT    NOT NULL,
    external_platform           TEXT,
    external_score              REAL,
    status                      TEXT    NOT NULL DEFAULT 'PENDING',
    instructor_recommendation   TEXT,
    instructor_note             TEXT,
    instructor_id               INTEGER REFERENCES users(id),
    admin_note                  TEXT,
    admin_id                    INTEGER REFERENCES users(id),
    submitted_at                TEXT    NOT NULL DEFAULT (datetime('now')),
    reviewed_by_instructor_at   TEXT,
    decided_by_admin_at         TEXT
);
```

| Column | Type | Notes |
|--------|------|-------|
| `pathway` | TEXT | `TRANSFER`, `ASSESSMENT`, `EXEMPTION` |
| `status` | TEXT | `PENDING`, `INSTRUCTOR_REVIEWED`, `APPROVED`, `REJECTED`, `INFO_REQUESTED` |
| `evidence_description` | TEXT | Minimum 30 characters enforced by service layer |
| `external_score` | REAL | Nullable — optional external assessment score |

**Workflow stages:**
```
PENDING
  → (instructor reviews) → INSTRUCTOR_REVIEWED
    → (admin approves)   → APPROVED  (transfer_credit auto-called)
    → (admin rejects)    → REJECTED
  → (instructor requests info) → INFO_REQUESTED (stays with learner)
```

---

### COURSE_SUBMISSIONS

```sql
CREATE TABLE IF NOT EXISTS course_submissions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code     TEXT    NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    instructor_id   INTEGER NOT NULL REFERENCES users(id),
    status          TEXT    NOT NULL DEFAULT 'PENDING',
    instructor_note TEXT,
    admin_note      TEXT,
    submitted_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    decided_at      TEXT
);
```

| Column | Type | Notes |
|--------|------|-------|
| `status` | TEXT | `PENDING`, `APPROVED`, `REJECTED` |
| `instructor_note` | TEXT | Nullable — submission message |
| `admin_note` | TEXT | Nullable — approval/rejection reason |

---

### NOTIFICATIONS

```sql
CREATE TABLE IF NOT EXISTS notifications (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message           TEXT    NOT NULL,
    notification_type TEXT    NOT NULL DEFAULT 'INFO',
    is_read           INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

| Column | Type | Notes |
|--------|------|-------|
| `notification_type` | TEXT | `INFO`, `SUCCESS`, `WARNING`, `ERROR` |
| `is_read` | INTEGER | `0` = unread, `1` = read |

---

### SCHEMA_VERSION

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Tracks which migrations have been applied. The `Database.initialize()`
method reads this table and runs only the migrations not yet applied.

---

## 4. Schema Migrations

All migrations are defined in `repository/database.py` and run
automatically on `Database.initialize()`. They are **additive only**
(no DROP TABLE, no DROP COLUMN) — safe to run on an existing database.

### v1 — Performance Indexes

```sql
-- Applied when: schema_version has no row for version 1
-- Purpose: speed up the most common queries

CREATE INDEX IF NOT EXISTS idx_enrollments_learner
    ON enrollments(learner_id);

CREATE INDEX IF NOT EXISTS idx_enrollments_course
    ON enrollments(course_code);

CREATE INDEX IF NOT EXISTS idx_progress_learner
    ON course_progress(learner_id);

CREATE INDEX IF NOT EXISTS idx_notifications_user
    ON notifications(user_id);
```

### v2 — Workflow Tables

```sql
-- Applied when: schema_version has no row for version 2
-- Purpose: add PLR, course submissions, and notifications

CREATE TABLE IF NOT EXISTS prior_learning_requests ( ... );
CREATE TABLE IF NOT EXISTS course_submissions ( ... );
CREATE TABLE IF NOT EXISTS notifications ( ... );
```

### v3 — Account Activation

```sql
-- Applied when: schema_version has no row for version 3
-- Purpose: support admin approval workflow for self-registration

ALTER TABLE users ADD COLUMN is_active        INTEGER NOT NULL DEFAULT 1;
ALTER TABLE users ADD COLUMN account_status   TEXT    NOT NULL DEFAULT 'ACTIVE';
ALTER TABLE users ADD COLUMN rejection_reason TEXT;
ALTER TABLE users ADD COLUMN full_name        TEXT    NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN email            TEXT    NOT NULL DEFAULT '';
```

### v4 — Profile Management

```sql
-- Applied when: schema_version has no row for version 4
-- Purpose: support full profile editing for all roles

ALTER TABLE users ADD COLUMN bio                  TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN preferred_difficulty TEXT DEFAULT NULL;
ALTER TABLE users ADD COLUMN profile_updated_at   TEXT DEFAULT NULL;
```

### Migration Pattern

```python
def initialize(self):
    """Create all tables and run pending migrations."""
    with self.transaction() as conn:
        self._create_base_tables(conn)
        current = self._get_schema_version(conn)
        if current < 1:
            self._migrate_v1(conn)
            self._set_schema_version(conn, 1)
        if current < 2:
            self._migrate_v2(conn)
            self._set_schema_version(conn, 2)
        if current < 3:
            self._migrate_v3(conn)
            self._set_schema_version(conn, 3)
        if current < 4:
            self._migrate_v4(conn)
            self._set_schema_version(conn, 4)
```

---

## 5. Indexes

| Index Name | Table | Columns | Purpose |
|-----------|-------|---------|---------|
| `idx_enrollments_learner` | enrollments | `learner_id` | Fast lookup of all enrollments for a learner |
| `idx_enrollments_course` | enrollments | `course_code` | Fast lookup of all learners in a course |
| `idx_progress_learner` | course_progress | `learner_id` | Fast progress summary per learner |
| `idx_notifications_user` | notifications | `user_id` | Fast unread notification count |
| `UNIQUE(learner_id, course_code)` | enrollments | Both | Prevents duplicates + acts as composite index |
| `UNIQUE(learner_id, course_code)` | course_progress | Both | Prevents duplicates + acts as composite index |
| `UNIQUE(course_code, prerequisite_code)` | prerequisites | Both | Prevents duplicate edges + acts as composite index |

---

## 6. Key Query Patterns

### Get a Learner's Completed Courses

```sql
SELECT course_code
FROM   enrollments
WHERE  learner_id = ?
AND    status = 'COMPLETED';
```

Used by: `LearnerRepo._get_completed_courses()`,
`PrerequisiteValidator.can_enroll()`

---

### Get All Prerequisites for a Course

```sql
SELECT prerequisite_code
FROM   prerequisites
WHERE  course_code = ?;
```

Used by: `CourseRepo.get_prerequisites()`, `CourseGraph.build_from_courses()`

---

### Build the Full Prerequisite Graph

```sql
SELECT course_code, prerequisite_code
FROM   prerequisites;
```

Used by: `CourseGraph.build_from_courses()` on service initialization

---

### Enrollment Duplicate Check

```sql
SELECT id
FROM   enrollments
WHERE  learner_id  = ?
AND    course_code = ?;
```

Used by: `EnrollmentService.enroll_learner()` before inserting.
The `UNIQUE` constraint provides database-level defense-in-depth.

---

### Atomic Enrollment Creation

```sql
-- Both run inside a single transaction
INSERT INTO enrollments (learner_id, course_code, status)
VALUES (?, ?, 'ENROLLED');

INSERT INTO course_progress (learner_id, course_code, percentage, completion_status)
VALUES (?, ?, 0.0, 'NOT_STARTED');
```

---

### Course Completion Rate

```sql
SELECT
    COUNT(*)                                          AS enrolled,
    SUM(CASE WHEN status='COMPLETED'  THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN status='IN_PROGRESS' THEN 1 ELSE 0 END) AS in_progress,
    SUM(CASE WHEN status='CANCELLED'  THEN 1 ELSE 0 END) AS cancelled
FROM enrollments
WHERE course_code = ?;
```

---

### Monthly Enrollment Trend (Last 6 Months)

```sql
SELECT
    strftime('%Y-%m', enrolled_at) AS month,
    COUNT(*)                        AS count
FROM   enrollments
WHERE  enrolled_at >= date('now', '-6 months')
GROUP  BY strftime('%Y-%m', enrolled_at)
ORDER  BY month;
```

---

### Learner Activity Report

```sql
SELECT
    l.id,
    l.name,
    COUNT(e.id)                                                AS enrolled,
    SUM(CASE WHEN e.status='COMPLETED'  THEN 1 ELSE 0 END)   AS completed,
    SUM(CASE WHEN e.status='IN_PROGRESS' THEN 1 ELSE 0 END)  AS in_progress,
    AVG(CASE WHEN e.status='COMPLETED'  THEN e.score END)     AS average_score
FROM   learners l
LEFT JOIN enrollments e ON e.learner_id = l.id
GROUP  BY l.id
ORDER  BY completed DESC;
```

---

### Pending Registrations

```sql
SELECT *
FROM   users
WHERE  account_status = 'PENDING'
ORDER  BY created_at ASC;
```

---

### Unread Notification Count

```sql
SELECT COUNT(*)
FROM   notifications
WHERE  user_id = ?
AND    is_read = 0;
```

---

## 7. Connection Management

### Pattern: Connection Per Operation

```python
class Database:

    def get_connection(self) -> sqlite3.Connection:
        """Open a new connection for a single operation."""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row      # dict-like row access
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def transaction(self):
        """Atomic transaction — commits on success, rolls back on error."""
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

**Why connection-per-operation?**

SQLite connections are lightweight. Opening a new connection per
operation is the safest pattern when multiple users (desktop + web)
may write to the same file simultaneously. WAL mode allows concurrent
reads while a write is in progress.

### PRAGMA Settings

| PRAGMA | Value | Reason |
|--------|-------|--------|
| `journal_mode` | `WAL` | Concurrent readers + one writer |
| `foreign_keys` | `ON` | Enforce `REFERENCES` constraints + `CASCADE` |

---

## 8. Integrity Rules

### Enforced at Database Level

| Rule | Mechanism |
|------|-----------|
| Unique username | `UNIQUE` constraint on `users.username` |
| Unique learner email | `UNIQUE` constraint on `learners.email` |
| One enrollment per learner/course | `UNIQUE(learner_id, course_code)` on `enrollments` |
| One progress per learner/course | `UNIQUE(learner_id, course_code)` on `course_progress` |
| No duplicate prerequisite edges | `UNIQUE(course_code, prerequisite_code)` on `prerequisites` |
| Cascade deletes | `ON DELETE CASCADE` on all FK references |
| Foreign key enforcement | `PRAGMA foreign_keys = ON` on every connection |

### Enforced at Service Level

| Rule | Where |
|------|-------|
| No circular prerequisites | `CycleDetector.would_create_cycle()` before insert |
| Course must be PUBLISHED to enroll | `EnrollmentService.enroll_learner()` |
| Score must be 0–100 | `EnrollmentService.complete_enrollment()` |
| Password minimum 8 chars | `AuthService.register()`, `ProfileService.change_password()` |
| Evidence minimum 30 chars | `PriorLearningService.submit_request()` |
| Email format validation | `ProfileService.update_personal_info()` |
| Bio maximum 500 chars | `ProfileService.update_personal_info()` |
| Status transitions | `EnrollmentService`, `CourseService` |

---

## 9. Seed Data

**File:** `data/seed_data.sql`
**Script:** `seed_courses.py`

### Default Accounts

| Username | Role | Status |
|----------|------|--------|
| `admin` | ADMIN | ACTIVE |
| `learner` | LEARNER | ACTIVE |
| `analyst` | ANALYST | ACTIVE |
| `instructor` | INSTRUCTOR | ACTIVE |

All passwords stored as bcrypt hashes of the values shown in the
README default credentials table.

### Sample Courses

| Code | Name | Difficulty | Duration | Status |
|------|------|-----------|---------|--------|
| CS101 | Intro to Computer Science | BEGINNER | 40h | PUBLISHED |
| CS102 | Programming Fundamentals | BEGINNER | 35h | PUBLISHED |
| PY101 | Python Basics | BEGINNER | 30h | PUBLISHED |
| CS201 | Data Structures | INTERMEDIATE | 50h | PUBLISHED |
| CS301 | Algorithms | ADVANCED | 60h | PUBLISHED |
| ML101 | Machine Learning Intro | ADVANCED | 55h | PUBLISHED |

### Sample Prerequisites

| Course | Requires |
|--------|---------|
| CS201 | CS101 |
| CS201 | CS102 |
| CS301 | CS201 |
| ML101 | CS201 |

**Resulting graph:**
```
CS101 ──┐
         ├──► CS201 ──► CS301
CS102 ──┘         └──► ML101

PY101  (standalone — no prerequisites)
```

### Sample Learner Profile

One learner profile is created and linked to the default `learner`
account. It has no enrollments on first seed — the learner can explore
all published courses and enroll manually.