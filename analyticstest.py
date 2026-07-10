from services.analytics_service import AnalyticsService

# Initialize your service (adjust as needed)
analytics = AnalyticsService()

print("=== system_overview ===")
print(analytics.system_overview())

print("\n=== learner_activity_report ===")
print(analytics.learner_activity_report())

print("\n=== most_enrolled_courses ===")
print(analytics.most_enrolled_courses())

# Check if these methods exist
for method_name in [
    "performance_report",
    "student_performance_report",
    "completion_breakdown",
    "enrollment_metrics",
    "enrollment_trend",
    "instructor_report",
    "score_buckets",
    "performance_trend",
    "completion_by_course",
]:
    fn = getattr(analytics, method_name, None)
    if fn:
        try:
            print(f"\n=== {method_name} ===")
            print(fn())
        except Exception as e:
            print(f"\n=== {method_name} === ERROR: {e}")
    else:
        print(f"\n=== {method_name} === NOT FOUND")