from auth.session_manager import SessionManager
from core.user import User
from core.enums import UserRole

print('=== SESSION MANAGER VERIFICATION ===')
print()

# Reset for clean state
SessionManager.reset()

# Singleton test
s1 = SessionManager()
s2 = SessionManager()
s3 = SessionManager()
assert s1 is s2
assert s2 is s3
print(f's1 is s2: {s1 is s2} PASSED')
print(f's2 is s3: {s2 is s3} PASSED')
print('Singleton pattern: PASSED')

# Initial state
assert s1.is_authenticated() == False
assert s1.current_user() is None
print('Initial is_authenticated(): False PASSED')
print('Initial current_user(): None PASSED')

# Login
user = User('admin', '\$2b\$12\$fakehash', UserRole.ADMIN, id=1)
s1.login(user)
assert s1.is_authenticated() == True
assert s1.current_user() is user
print(f'After login: is_authenticated={s1.is_authenticated()} PASSED')
print(f'current_user: {s1.current_user().username} PASSED')

# Shared state across references
assert s2.is_authenticated() == True
assert s2.current_user() is user
print('State shared across all references: PASSED')

# Logout
s1.logout()
assert s1.is_authenticated() == False
assert s1.current_user() is None
assert s2.is_authenticated() == False
print('After logout: is_authenticated=False PASSED')
print('State cleared across all references: PASSED')

# Login with None raises
try:
    s1.login(None)
    print('FAILED - should have raised')
except ValueError as e:
print(f'login(None) raises ValueError: PASSED')

# repr
print(f'repr: {repr(s1)}')

print()
print('SESSION MANAGER OK')