# LMPTS — Complete Feature Guide

The **Learning Management & Prerequisite Tracking System (LMPTS)** manages
courses, prerequisite relationships, learner enrollment, and analytics for
four roles: **Admin**, **Instructor**, **Learner**, and **Analyst**. It
ships with two front ends — a Tkinter desktop app (`gui/`) and a Flask web
app (`webapp/`) — both built on the same `core/ → auth/ → algorithms/ →
repository/ → services/` layers, so business rules are identical no matter
which UI is used.

This document is the single index of every feature in the project. For a
deep dive on the analytics dashboard specifically, see
[`analytics_dashboard.md`](analytics_dashboard.md).

---

## 1. Architecture

```
core/         domain models + enums + exceptions (no framework dependency)
auth/         password hashing, auth service, in-memory session (desktop only)
algorithms/   graph, cycle detection, path finding, prerequisite validation, recommendation scoring
repository/   SQLite persistence, one repo per aggregate, connection-per-operation
services/     business logic / use cases — the layer both UIs call into
gui/          Tkinter desktop UI
webapp/       Flask web UI (Blueprints + Jinja2 templates)
data/         SQLite database file + schema/seed SQL
tests/        pytest suite (unit + integration)
docs/         architecture, API contracts, database design, this file
```

Both `gui/app.py:create_services()` and `webapp/__init__.py:create_app()`
wire up the exact same service objects against one shared `Database`
instance — no logic is duplicated between the two front ends.

---

## 2. Accounts, Authentication & Roles

- **Four roles**: `ADMIN`, `INSTRUCTOR`, `LEARNER`, `ANALYST` (`core/enums.py:UserRole`).
- **Login** (`AuthService.login`) — bcrypt password verification; rejects
  login with a specific reason if the account is `PENDING`, `REJECTED`,
    `INACTIVE`, or a plain wrong password.
    - **Two ways to create an account**:
      - **Admin-created** (`AuthService.register`) — any role, account is
          `ACTIVE` immediately.
            - **Self-registration** (`AuthService.register_learner`) — learners only,
                account starts `PENDING` and cannot log in until an admin approves it.
                - **Account status workflow** (`core/enums.py:AccountStatus`):
                  `PENDING → ACTIVE` (approved) or `PENDING → REJECTED` (with a required
                    reason), plus `ACTIVE ⇄ INACTIVE` (admin deactivate/reactivate).
                    - **Admin approval screens** — Pending Registrations (GUI:
                      `gui/admin/pending_registrations.py`, Web: `/admin/registrations`):
                        approve (optional welcome note), reject (mandatory reason), request more
                          information (keeps it pending), deactivate/reactivate any user. Backed by
                            `services/account_service.py`.
                            - **Default seeded accounts**: `admin/admin123`, `learner/learner123`,
                              `analyst/analyst123`, `instructor/instructor123`.
                              - **Notifications on registration** — every admin gets an in-app
                                notification when a learner self-registers.

                                ### Profile management (all roles)
                                `services/profile_service.py`, GUI: `gui/profile/`, Web: `/profile/`
                                - **Personal information** — edit full name, email, bio (≤500 chars);
                                  learners additionally set a preferred difficulty level. Editing a
                                    learner's name/email keeps their linked `Learner` record in sync.
                                    - **Change password** — requires the current password, enforces 8+ chars /
                                      1 uppercase / 1 digit / must differ from the old password, sends a
                                        security notification, and forces re-login on success.
                                        - **Account details** — read-only view of user ID, role, account status,
                                          active flag, member-since date, last profile edit.
                                          - **Password strength meter** — `ProfileService.calculate_password_strength()`
                                            (score/label/color/issues), used live on both registration and password
                                              change forms in the GUI.

                                              ---

                                              ## 3. Course Management

                                              `services/course_service.py`
                                              - Create / update / delete courses (code, name, description, difficulty,
                                                duration).
                                                - Lifecycle: `DRAFT → PUBLISHED → ARCHIVED`. Only `PUBLISHED` courses are
                                                  open for learner enrollment.
                                                  - **Prerequisites** — add/remove prerequisite edges on a directed course
                                                    graph (`algorithms/graph.py`); adding an edge that would create a cycle
                                                      is rejected (`algorithms/cycle_detection.py` → `CircularDependencyError`).
                                                      - **Study order** — topological sort of the whole curriculum into ordered
                                                        levels (`get_course_levels`), shown as the prerequisite DAG in both UIs.

                                                        ### Instructor course submission & admin approval
                                                        - Instructors create courses as `DRAFT` and edit them freely while in that
                                                          state (`gui/instructor/course_manager.py`, Web: `/instructor/courses`).
                                                            They cannot publish directly.
                                                            - **Submit for review** — inserts a row into `course_submissions` and
                                                              notifies every admin.
                                                              - **Admin Course Approvals** (`gui/admin/course_approvals.py`, Web:
                                                                `/admin/course-approvals`) — review pending submissions, **Approve &
                                                                  Publish** (publishes the course + notifies the instructor) or **Reject**
                                                                    (mandatory feedback note, instructor notified, course stays a draft to
                                                                      revise and resubmit).

                                                                      ---

                                                                      ## 4. Enrollment & Progress

                                                                      `services/enrollment_service.py`, `services/progress_service.py`
                                                                      - **Enroll** — blocked if the course isn't published, if prerequisites
                                                                        aren't met (missing prerequisites are returned so the UI can list them),
                                                                          or if the learner already has *any* enrollment record for that course —
                                                                            regardless of its status — since the `enrollments` table is unique per
                                                                              `(learner_id, course_code)`. (This duplicate check was hardened during
                                                                                Flask integration: it previously only covered `ENROLLED`/`IN_PROGRESS`
                                                                                  and let a re-enrollment attempt on a `COMPLETED`/`CANCELLED` course crash
                                                                                    with an unhandled `sqlite3.IntegrityError` instead of a friendly message.)
                                                                                    - **Start** — `ENROLLED → IN_PROGRESS`.
                                                                                    - **Complete** — records a 0–100 score, marks `COMPLETED`.
                                                                                    - **Cancel** — direct cancellation (learner or admin action).
                                                                                    - **Progress tracking** — a separate `course_progress` record per
                                                                                      enrollment (0–100%), auto-transitioning `NOT_STARTED → IN_PROGRESS →
                                                                                        COMPLETED`, plus a `FAILED` terminal state.
                                                                                        - **Transfer credit / exemption** (admin-only) — grants credit for a
                                                                                          course without the learner completing it in-system, used for prior
                                                                                            learning approvals and manual admin overrides.

                                                                                            ### Cancellation requests (desktop GUI only, not yet in the web app)
                                                                                            `core/cancellation_request.py`, `services/enrollment_service.py`,
                                                                                            `gui/instructor/cancellation_review.py`
                                                                                            - A learner can request to cancel an enrollment **only if it hasn't been
                                                                                              started yet** (status `ENROLLED`).
                                                                                              - Workflow: learner submits (`PENDING`, with a reason) → instructor
                                                                                                **approves** (enrollment + progress record deleted, learner can
                                                                                                  re-enroll later) or **rejects** (enrollment continues unchanged) → the
                                                                                                    learner can also **withdraw** their own pending request.
                                                                                                    - Instructor-facing review queue lists all pending requests across
                                                                                                      learners.

                                                                                                      ---

                                                                                                      ## 5. Prior Learning Credit

                                                                                                      `services/prior_learning_service.py`, `core/prior_learning_request.py`
                                                                                                      Three pathways a learner can claim credit through: **Transfer Credit**,
                                                                                                      **Prior Assessment**, **Exemption Request** — each backed by a written
                                                                                                      evidence description (min. 30 characters) and an optional external
                                                                                                      platform/score (e.g. a Coursera certificate).

                                                                                                      Two-stage review:
                                                                                                      1. **Instructor review** (`gui/instructor/plr_review.py`, Web:
                                                                                                         `/instructor/plr`) — recommends `APPROVE` / `REJECT` / `INFO_REQUESTED`
                                                                                                            with a note.
                                                                                                            2. **Admin final decision** (`gui/admin/plr_approval.py`, Web:
                                                                                                               `/admin/plr`) — sees the instructor's recommendation, makes the binding
                                                                                                                  `APPROVED`/`REJECTED` call; an approval automatically grants transfer
                                                                                                                     credit for the course.

                                                                                                                     Learners track their own requests and see instructor/admin notes at every
                                                                                                                     stage (`gui/learner/prior_learning.py`, Web: `/learner/prior-learning`).

                                                                                                                     ---

                                                                                                                     ## 6. Learning Path & Recommendations

                                                                                                                     `services/learning_path_service.py`, `services/recommendation_service.py`,
                                                                                                                     `algorithms/path_finder.py`
                                                                                                                     - **Roadmap to a goal course** — given a target course, computes completed
                                                                                                                       / in-progress / remaining prerequisites and an overall completion
                                                                                                                         percentage (GUI: Learning Path screen, Web: `/learner/path`).
                                                                                                                         - **Course recommendations** — scores unenrolled courses by difficulty
                                                                                                                           preference and prerequisite readiness, with human-readable reasons per
                                                                                                                             recommendation, plus a one-click enroll action (Web: `/learner/recommendations`).

                                                                                                                             ---

                                                                                                                             ## 7. Analytics & Reporting

                                                                                                                             `services/analytics_service.py` — read-only, computed fresh from the
                                                                                                                             database on every request (no caching).

                                                                                                                             - **System overview** — total courses/learners/enrollments/completions,
                                                                                                                               overall completion rate, difficulty distribution.
                                                                                                                               - **Per-course stats** — completion rate, dropout rate, most-enrolled
                                                                                                                                 courses, average score by course, bottleneck detection (courses above a
                                                                                                                                   configurable dropout threshold), prerequisite-chain length per course.
                                                                                                                                   - **Per-learner activity report** — enrolled/completed/in-progress counts,
                                                                                                                                     completion rate, average score, ranked list across all learners.
                                                                                                                                     - **Chart-driven Analytics Dashboard** (Web: `/analyst/`, guarded for
                                                                                                                                       ANALYST and ADMIN) — a from-scratch redesign with five sections and 10
                                                                                                                                         Chart.js charts (student performance, course completion, enrollment
                                                                                                                                           trends, instructor analytics), every table/chart degrading gracefully to
                                                                                                                                             a "No Data Available" state instead of crashing on an empty database.
                                                                                                                                               **Full write-up:** [`analytics_dashboard.md`](analytics_dashboard.md).
                                                                                                                                               - The desktop GUI has an equivalent (table + one matplotlib bar chart)
                                                                                                                                                 analytics dashboard shared between the Admin and Analyst roles.

                                                                                                                                                 ---

                                                                                                                                                 ## 8. Notifications

                                                                                                                                                 `repository/prior_learning_repo.py:NotificationRepository`,
                                                                                                                                                 `core/notification.py`
                                                                                                                                                 In-app notifications (info/success/warning/error) delivered to a user's
                                                                                                                                                 account for: new learner registrations (→ admins), registration
                                                                                                                                                 approval/rejection/info-request (→ learner), account deactivation (→
                                                                                                                                                 user), course submission (→ admins), course approval/rejection (→
                                                                                                                                                 instructor), prior-learning status changes, and profile email/password
                                                                                                                                                 changes. Instructors can mark all their notifications read from their
                                                                                                                                                 dashboard.

                                                                                                                                                 ---

                                                                                                                                                 ## 9. Desktop GUI (Tkinter)

                                                                                                                                                 One dashboard per role, routed by `gui/main_window.py` based on the logged
                                                                                                                                                 in user's role:

                                                                                                                                                 | Role | Screens |
                                                                                                                                                 |---|---|
                                                                                                                                                 | **Admin** | Dashboard, Pending Registrations, Courses, Course Approvals, Prerequisites, Learners, Users, Prior Learning, Analytics, My Profile |
                                                                                                                                                 | **Instructor** | Dashboard, My Courses, Monitor Learners, Prior Learning Review, Review Cancellation Requests, Course Reports, My Profile |
                                                                                                                                                 | **Learner** | Dashboard, My Courses, Learning Path, Progress, Prior Learning, Recommendations, My Profile |
                                                                                                                                                 | **Analyst** | Dashboard, Reports, Completion Stats, Bottlenecks, My Profile |

                                                                                                                                                 Shared widgets: reusable course table, prerequisite graph canvas
                                                                                                                                                 (`gui/widgets/graph_view.py`), password strength meter, sidebar nav,
                                                                                                                                                 confirm/info/error dialogs.

                                                                                                                                                 ---

                                                                                                                                                 ## 10. Web Application (Flask)

                                                                                                                                                 `webapp/` — a server-rendered (Jinja2) port of the same role-based screens,
                                                                                                                                                 built as a Flask Blueprint per role plus shared `auth`/`profile`
                                                                                                                                                 blueprints. Entry point: `python run_web.py` → `http://127.0.0.1:5000`.

                                                                                                                                                 **Design decisions specific to the web port:**
                                                                                                                                                 - **Session handling** — identity is tracked with Flask's own signed
                                                                                                                                                   cookie session (`session['user_id']`), not the desktop app's
                                                                                                                                                     `SessionManager` singleton (that class holds one process-wide "current
                                                                                                                                                       user" slot, which is correct for a single-user desktop app but would let
                                                                                                                                                         concurrent web users overwrite each other's login state).
                                                                                                                                                           `AuthService.login()`/`register_learner()` are still the source of truth
                                                                                                                                                             for credential checks and business rules.
                                                                                                                                                             - **Role gating** — a `role_required(*roles)` decorator (403 on mismatch)
                                                                                                                                                               guards every blueprint; `login_required` guards the shared profile
                                                                                                                                                                 routes.
                                                                                                                                                                 - No JS framework/build step — plain HTML forms + Jinja2 + one shared
                                                                                                                                                                   `static/style.css`; Chart.js (analytics dashboard only) is the sole
                                                                                                                                                                     CDN dependency, loaded through a `{% block scripts %}` slot in the base
                                                                                                                                                                       template.
                                                                                                                                                                       - **Feature parity gap**: cancellation requests currently exist only in
                                                                                                                                                                         the desktop GUI — the web app does not yet have `/learner/*/cancel` or
                                                                                                                                                                           an instructor cancellation-review route.

                                                                                                                                                                           ---

                                                                                                                                                                           ## 11. Testing

                                                                                                                                                                           `tests/` — pytest, real SQLite repositories against temporary databases
                                                                                                                                                                           (no mocking of the persistence layer). Coverage spans core models, auth,
                                                                                                                                                                           algorithms, every repository, every service, and integration tests that
                                                                                                                                                                           exercise a full enroll → progress → complete flow. The analytics dashboard
                                                                                                                                                                           rewrite alone added 20 new tests for the 8 new `AnalyticsService` methods.

                                                                                                                                                                           ```bash
                                                                                                                                                                           pytest                 # run everything
                                                                                                                                                                           pytest --cov           # with coverage report
                                                                                                                                                                           ```

                                                                                                                                                                           ---

                                                                                                                                                                           ## 12. Tech Stack

                                                                                                                                                                           Python 3.11 · SQLite (WAL mode) · Tkinter (desktop UI) · Flask + Jinja2
                                                                                                                                                                           (web UI) · Chart.js via CDN (analytics charts) · bcrypt (password hashing)
                                                                                                                                                                           · pytest / pytest-cov (testing) · matplotlib (desktop analytics chart).
                                                                                                                                                                           