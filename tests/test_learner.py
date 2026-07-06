from core.learner import Learner
from core.exceptions import ValidationError, EnrollmentError

print('=== LEARNER VERIFICATION ===')
print()

# Create learner
learner = Learner(
    name='Alice Smith',
    email='alice@example.com',
    user_id=1
)
print(f'Created: {repr(learner)}')

# Verify types (UML: sets)
assert isinstance(learner.completed_courses, set)
assert isinstance(learner.current_courses, set)
print(f'completed_courses type: {type(learner.completed_courses).__name__} PASSED')
print(f'current_courses type:   {type(learner.current_courses).__name__} PASSED')

# Validate
learner.validate()
print('validate(): PASSED')

# Enroll
learner.enroll('CS101')
assert 'CS101' in learner.current_courses
print(f'enroll CS101: current={learner.current_courses} PASSED')

# Progress with one current
p = learner.progress()
print(f'progress() with 1 current: {p}% (expected 0.0%)')

# Complete
learner.complete('CS101')
assert 'CS101' in learner.completed_courses
assert 'CS101' not in learner.current_courses
print(f'complete CS101: completed={learner.completed_courses} PASSED')

# Progress after completion
learner.enroll('CS201')
p = learner.progress()
print(f'progress() 1 done / 2 total: {p}% (expected 50.0%)')
assert p == 50.0

# completion_rate
cr = learner.completion_rate()
assert cr == p
print(f'completion_rate() == progress(): PASSED')

# Cannot re-enroll completed
try:
    learner.enroll('CS101')
    print('FAILED - should have raised')
except EnrollmentError as e:
    print(f'Re-enroll completed raises EnrollmentError: PASSED')

# Cannot complete unenrolled
try:
    learner.complete('CS999')
    print('FAILED - should have raised')
except EnrollmentError as e:
    print(f'Complete unenrolled raises EnrollmentError: PASSED')

# to_dict
d = learner.to_dict()
assert isinstance(d['completed_courses'], list)
assert isinstance(d['current_courses'], list)
print('to_dict() converts sets to lists: PASSED')

print()
print('LEARNER OK')
