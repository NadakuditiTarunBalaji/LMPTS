# Changelog

All notable changes to LMPTS are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] - 2026-07-01

### Added

#### Core System
- Domain models: `User`, `Learner`, `Course`, `Enrollment`,
  `CourseProgress`, `PriorLearningRequest`, `CancellationRequest`,
  `Notification`, `UserProfile`
- Full enumeration set: `UserRole`, `CourseStatus`, `EnrollmentStatus`,
  `DifficultyLevel`, `CompletionStatus`, `AccountStatus`
- Custom exception hierarchy rooted at `LMPTSException`

#### Authentication & Accounts
- bcrypt password hashing via `PasswordManager`
- Login with account-status-aware rejection messages
- Admin-created accounts (any role, immediately `ACTIVE`)
- Learner self-registration (starts `PENDING`, requires admin approval)
- Account status workflow: `PENDING → ACTIVE / REJECTED`,
  `ACTIVE ⇄ INACTIVE`
- Singleton `SessionManager` for desktop session tracking
- Flask cookie-based session for web (`session['user_id']`)

#### Course Management
- Full CRUD for courses (code, name, description, difficulty, duration)
- Course lifecycle: `DRAFT → PUBLISHED → ARCHIVED`
- Instructor course submission workflow → admin approve/reject
- Only `PUBLISHED` courses open for enrollment

#### Prerequisite Graph
- Directed Acyclic Graph (`CourseGraph`) with forward + reverse edges
- DFS cycle detection (`CycleDetector`) — rejects circular prerequisites
- Topological sort via Kahn's algorithm (`TopologicalSorter`)
- BFS shortest path finder (`PathFinder`)
- Transitive prerequisite calculation (all ancestors)

#### Enrollment & Progress
- Prerequisite validation before enrollment
  (`satisfied = completed ∪ transfers ∪ exemptions ∪ placement`)
- Enrollment state machine: `ENROLLED → IN_PROGRESS → COMPLETED / CANCELLED`
- Fine-grained progress tracking: 0–100 % with auto-status adjustment
- `FAILED` terminal progress state
- Atomic transactions: enrollment + progress created together
- Duplicate enrollment hardened against `sqlite3.IntegrityError`
- Transfer credit and exemption grants (admin only)

#### Cancellation Request Workflow (Desktop)
- Learner requests cancellation (only if status = `ENROLLED`)
- Instructor approves (deletes enrollment) or rejects
- Learner can withdraw their own `PENDING` request

#### Prior Learning / Transfer Credit
- Three pathways: Transfer Credit / Prior Assessment / Exemption
- Evidence description (min. 30 chars) + optional platform/score
- Two-stage review: Instructor recommendation → Admin final decision
- Approval auto-calls `transfer_credit()` for the course

#### Learning Paths & Recommendations
- BFS shortest path to any goal course
- Personalized roadmap with completed/remaining breakdown
- Multi-factor recommendation scoring (prereq readiness 40 %,
  difficulty match 30 %, path length 20 %, duration 10 %)
- Human-readable reasons per recommendation

#### Analytics & Reporting
- System overview: courses, learners, enrollments, completion rate
- Per-course: completion rate, dropout rate, average score, chain length
- Bottleneck detection (configurable dropout threshold)
- Learner activity report ranked by completion rate
- 8 new `AnalyticsService` methods for the web dashboard
- Grade conversion: score → A/B/C/D/F letter grade
- Score bucketing: Excellent / Good / Average / Poor

#### Desktop GUI (Tkinter)
- Role-based dashboards: Admin, Instructor, Learner, Analyst
- Sidebar navigation with hover + active states
- Prerequisite graph canvas (`GraphView`)
- Sortable course table (`CourseTable`)
- Live password strength meter
- Confirm / error / info / warning dialogs
- Full cancellation request review screen (instructor)

#### Web Application (Flask)
- Flask Blueprint per role: admin, instructor, learner, analyst, profile
- `auth_utils.py`: `role_required()` decorator + `login_required`
- Server-rendered Jinja2 templates
- Flash message partial (`_flashes.html`)
- Custom error pages: 403, 404
- Chart-driven analytics dashboard with 10 Chart.js charts:
  - Student Performance: bar + pie + line
  - Course Completion: doughnut + stacked bar
  - Enrollment Analytics: bar + line
  - Instructor Analytics: horizontal bar
- Chart.js bundled locally (`static/js/chart.umd.min.js`)
- Responsive layout (collapses to single column below 900 px)
- Graceful empty-state on every table and chart
- Pending account screen (`auth/pending.html`)
- Analyst has 5 dedicated template pages

#### Notifications
- In-app notifications (Info / Success / Warning / Error)
- Events: registration, PLR, course approval, cancellation,
  password/email change, account deactivation/reactivation

#### Database
- SQLite with WAL journal mode
- Connection-per-operation pattern
- Schema migration system (v1–v4)
- `seed_data.sql` for sample courses and accounts
- `seed_courses.py` utility script

#### Testing
- 540+ tests across 20+ test files
- Real SQLite repositories against `tmp_path` temp databases
- `InMemoryUserRepository` for fast unit tests
- Integration tests: full enroll → progress → complete flow
- Analytics empty-database guards (divide-by-zero protection)
- 33 analytics service tests (13 pre-existing + 20 new)

---

## [Unreleased]

### Planned
- Cancellation request workflow ported to web app
- CSV / PDF export for analytics tables
- Notification bell with badge count in web header
- Auto-refresh dashboard data
- Dark mode toggle
- PostgreSQL support
- REST API (Flask / FastAPI)
- Docker deployment
- Email notifications for PLR decisions