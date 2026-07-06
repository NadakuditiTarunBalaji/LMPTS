from core.enrollment import Enrollment
from core.enums import EnrollmentStatus
from core.exceptions import ValidationError, EnrollmentError

print('=== ENROLLMENT VERIFICATION ===')
print()

# Create
e = Enrollment(learner_id=1, course_code='CS101')
print(f'Created: {repr(e)}')
assert e.status == EnrollmentStatus.ENROLLED
print(f'Initial status: {e.status.value} PASSED')

# Validate
e.validate()
print('validate(): PASSED')

# State machine: ENROLLED → IN_PROGRESS
e.start()
assert e.status == EnrollmentStatus.IN_PROGRESS
print(f'start(): {e.status.value} PASSED')

# State machine: IN_PROGRESS → COMPLETED
e.complete(92)
assert e.status == EnrollmentStatus.COMPLETED
assert e.score == 92
assert e.completed_at is not None
print(f'complete(92): status={e.status.value}, score={e.score} PASSED')

# Terminal state: cannot cancel after complete
try:
    e.cancel()
    print('FAILED - should have raised')
except EnrollmentError as ex:
    print(f'Cancel after complete raises EnrollmentError: PASSED')

# Fresh: ENROLLED → CANCELLED
e2 = Enrollment(learner_id=2, course_code='CS201')
e2.cancel()
assert e2.status == EnrollmentStatus.CANCELLED
print(f'cancel() from ENROLLED: {e2.status.value} PASSED')

# Terminal state: cannot complete after cancel
try:
    e2.complete(80)
    print('FAILED - should have raised')
except EnrollmentError as ex:
    print(f'Complete after cancel raises EnrollmentError: PASSED')

# Score validation
e3 = Enrollment(learner_id=3, course_code='CS301')
try:
    e3.complete(150)
    print('FAILED - should have raised')
except ValidationError as ex:
    print(f'Score > 100 raises ValidationError: PASSED')

# Edge scores
e4 = Enrollment(learner_id=4, course_code='CS401')
e4.complete(0)
assert e4.score == 0
print('Score of 0 is valid: PASSED')

e5 = Enrollment(learner_id=5, course_code='CS501')
e5.complete(100)
assert e5.score == 100
print('Score of 100 is valid: PASSED')

# to_dict
d = e.to_dict()
assert d['status'] == 'COMPLETED'
assert d['score'] == 92
print(f'to_dict(): {d}')
print('to_dict(): PASSED')

print()
print('ENROLLMENT OK')
