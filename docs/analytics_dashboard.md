# Analytics Dashboard — Feature Guide

This document describes everything added/changed to redesign the Analytics
Dashboard (`/analyst/`) from a static, table-only page into a dynamic,
chart-driven dashboard with five sections. It covers the feature set, the
data each section is built from, and every file that was touched.

Audience: ANALYST and ADMIN roles (the route is guarded for both).

---

## 1. What changed, at a glance

| Before | After |
|---|---|
| A handful of stat cards + 2 plain HTML tables | 5 sections: Overview, Student Performance, Course Completion, Enrollment Analytics, Instructor Analytics |
| No charts anywhere in the web app | 10 Chart.js charts (bar, pie, line, doughnut, stacked bar, horizontal bar) |
| Data computed ad hoc in the route | 8 new `AnalyticsService` methods, each independently testable |
| No empty-state handling | Every table and every chart shows **"No Data Available"** when its underlying data is empty |
| Static on page load | Recomputed from the database on every request — no caching, no staleness |

No new frontend framework or build step was introduced. The app remains
pure Flask + Jinja2; Chart.js is loaded from a CDN and initialized from
data embedded via Jinja's `| tojson` filter.

---

## 2. Section 1 — Overview

Five stat cards, sourced from the pre-existing `AnalyticsService.system_overview()`:

- **Total Courses**
- **Total Students**
- **Total Enrollments**
- **Completed Courses**
- **Completion Rate**

No new backend logic here — this reuses the existing method that already
powered the old dashboard.

---

## 3. Section 2 — Student Performance

### Table
Columns: **Student Name, Course, Marks, Grade, Status**. One row per
enrollment in the system (not per student), so a student in 3 courses
produces 3 rows. Status is rendered as a colored badge:
- `COMPLETED` → green ("ok")
- `CANCELLED` → red ("bad")
- everything else (`ENROLLED`, `IN_PROGRESS`) → amber ("warn")

### New: Grade
Every enrollment's numeric `score` (0–100) is converted to a letter grade:

| Score | Grade |
|---|---|
| ≥ 90 | A |
| ≥ 80 | B |
| ≥ 70 | C |
| ≥ 60 | D |
| < 60 | F |
| no score yet | `N/A` |

### Charts
1. **Bar chart — Marks by Student**: one bar per scored enrollment
   (`student (course)` on the X axis, marks on Y). Unscored enrollments are
   excluded since they have no marks to plot.
2. **Pie chart — Performance Distribution**: every scored enrollment is
   bucketed into **Excellent / Good / Average / Poor**:

   | Score | Bucket |
   |---|---|
   | ≥ 90 | Excellent |
   | ≥ 75 | Good |
   | ≥ 50 | Average |
   | < 50 | Poor |

3. **Line chart — Performance Over Time**: average score of all courses
   *completed* in each of the last 6 calendar months. Months are always
   shown even if they have zero completions (the axis never has gaps),
   but a month with no completions is plotted as a genuine gap in the
   line rather than a misleading 0.

### Backend methods (`services/analytics_service.py`)
- `student_performance_report()` — the table rows.
- `score_bucket_distribution()` — the pie chart counts.
- `performance_trend(months=6)` — the line chart series.

---

## 4. Section 3 — Course Completion Analytics

Unlike Section 2 (which reads enrollment status), this section reads the
**`course_progress`** table — the system's fine-grained progress tracker,
which is the more accurate source for "how far along is this learner in
this specific course."

### Metrics (stat cards)
- **Completed**
- **In Progress**
- **Not Started**
- **Completion %**

> Note: `course_progress` has a 4th status, `FAILED`, which this dashboard
> folds into **Not Started** so the UI matches the 3-bucket spec that was
> requested, rather than exposing a 4th card/slice.

### Charts
1. **Doughnut chart** — the same Completed/In Progress/Not Started split
   as the stat cards, as a proportion of the whole system.
2. **Stacked bar chart** — the same 3-way split, but broken out **per
   course**, so you can see which specific courses have a backlog of
   not-started learners vs. which are mostly finished.

### Backend methods
- `course_completion_breakdown()` — system-wide counts + rate.
- `course_completion_by_course()` — per-course counts, shaped directly
  for Chart.js's stacked-bar format (`labels`, `completed`, `in_progress`,
  `not_started` arrays).

---

## 5. Section 4 — Enrollment Analytics

### Metrics (stat cards)
- **Total Enrollments**
- **New Enrollments (This Week)** — enrolled in the last 7 days
- **Monthly Enrollments** — enrolled in the current calendar month
- **Growth %** — this month's enrollment count vs. last month's
  (`(current - previous) / previous * 100`; if last month had zero
  enrollments, growth is reported as 100% if this month has any, else 0% —
  this avoids a divide-by-zero crash on a young/empty system)

### Charts
1. **Bar chart — Monthly Enrollments**: enrollment count per month, last
   6 months.
2. **Line chart — Enrollment Trend**: the exact same monthly series as
   the bar chart, rendered as a trend line — one is for reading exact
   monthly magnitude, the other for reading the overall shape/direction.

### Backend methods
- `enrollment_monthly_trend(months=6)` — shared by both charts.
- `enrollment_summary_metrics()` — the 4 stat cards.

---

## 6. Section 5 — Instructor Analytics

### Table
Columns: **Instructor Name, Courses Created, Students Assigned, Average
Rating, Completion Rate**.

- **Courses Created** — how many courses this instructor has submitted
  for review (via `course_submissions`) that weren't rejected.
- **Students Assigned** — the number of *distinct* learners enrolled
  across all of that instructor's courses (a learner in two of the
  instructor's courses is only counted once).
- **Completion Rate** — aggregate completion rate across all of that
  instructor's courses.
- **Average Rating** — always shows **`N/A`**. There is no ratings/feedback
  table anywhere in the database schema, so this is not a fake or
  hardcoded number dressed up as real data — it's an honest "not
  collected" indicator. (Decision made explicitly with the project owner
  rather than inventing a ratings feature or a proxy score.)

Instructors who haven't submitted any courses yet still appear in the
table with zeros, rather than being silently omitted — so the analyst can
see every instructor account that exists, not just active ones.

### Chart
**Horizontal bar chart** — Students Assigned per instructor. (Of the two
numbers in the table, this is the one chosen for the chart since it best
reflects instructor workload/impact.)

### Backend method
- `instructor_analytics(instructors, instructor_courses)` — takes the
  list of INSTRUCTOR-role users and a `{instructor_id: {course_codes}}`
  map (both fetched by the route, since course ownership lives in the
  `course_submissions` table, not in `AnalyticsService`'s existing
  dependencies) and returns the aggregated per-instructor stats.

---

## 7. "No Data Available" handling

Every table falls back to a `No Data Available` message when its list is
empty (reusing the existing `.empty-state` CSS class already used
elsewhere in the app). Every chart has a matching guard: before
constructing the `Chart.js` object, a JS check looks at whether the
relevant data is empty (an empty array, or all values summing to zero) —
if so, the `<canvas>` is hidden and a sibling "No Data Available" message
is shown instead, so charts never render as a blank box.

This was verified against the actual (near-empty) seed database, which
only creates courses and the 4 default accounts with no enrollments —
confirming every section degrades gracefully instead of crashing or
rendering broken charts.

---

## 8. Design & color choices

Chart colors follow a consistent, semantic scheme rather than arbitrary
per-chart colors, validated against the project's data-visualization
guidelines:

- **Magnitude charts with no category identity** (marks by student,
  monthly enrollments, students-per-instructor) use a single blue hue —
  color isn't trying to distinguish anything, so it doesn't vary.
- **Status-style charts** (completion doughnut/stacked bar, performance
  buckets) reuse the same 3–4 colors everywhere on the page so the same
  concept is always the same color:
  - Completed / Excellent → green
  - In Progress / Good → blue
  - Not Started / Average → amber
  - Poor → red
- Charts that sit side-by-side and could be confused (monthly enrollment
  bar vs. enrollment trend line) use two different hues (blue vs. aqua)
  purely to visually separate them.

All charts are responsive (`maintainAspectRatio: false` inside a
height-bounded container) and the whole dashboard collapses to a
single column below 900px, matching the app's existing responsive
breakpoint.

---

## 9. Files changed

| File | What changed |
|---|---|
| `repository/enrollment_repo.py` | Added `get_all_enrollments()` and `get_all_progress()` — system-wide reads used by the new analytics methods (previously only per-course/per-learner queries existed). |
| `services/analytics_service.py` | Added `_score_to_grade()` / `_score_to_bucket()` helpers and 8 new methods: `student_performance_report`, `score_bucket_distribution`, `performance_trend`, `course_completion_breakdown`, `course_completion_by_course`, `enrollment_monthly_trend`, `enrollment_summary_metrics`, `instructor_analytics`. |
| `webapp/analyst.py` | Rewrote the `dashboard()` route to compute and pass all 9 data pieces the template needs, including the raw `course_submissions` lookup for instructor course ownership. |
| `webapp/templates/base.html` | Added a `{% block scripts %}` slot before `</body>` so child templates can inject page-specific JS (Chart.js) without a global include. |
| `webapp/templates/analyst/dashboard.html` | Full rewrite: 5 sections, 2 tables, 10 charts, embedded JSON data, Chart.js initialization with empty-state guards. |
| `webapp/static/style.css` | Added `.chart-grid`, `.chart-container` (+ `.tall` variant), and `.section-title`, plus a responsive rule collapsing the chart grid to one column under 900px. |
| `tests/services/test_analytics_service.py` | 20 new tests covering the empty-database path (guards against divide-by-zero) and the populated path for every new method. |

---

## 10. Testing

- **Automated**: `pytest tests/services/test_analytics_service.py` — 33
  tests total (13 pre-existing + 20 new), all passing. The new tests use
  the same pattern as the existing suite: real SQLite repositories against
  a temporary database, not mocks.
- **Manual/end-to-end**: the Flask dev server was started, an ANALYST
  session was logged in, and `/analyst/` was fetched directly — confirmed
  a 200 response, correct stat-card values, correctly rendered
  student/instructor tables, and that all 7 chart data payloads embedded
  in the page are valid, well-formed JSON.

To try it yourself:
```bash
python run_web.py
# log in as analyst / analyst123 (or admin / admin123)
# visit http://127.0.0.1:5000/analyst/
```
