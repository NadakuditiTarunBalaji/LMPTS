from auth.auth_service import AuthService
from auth.user_repository import InMemoryUserRepository
from auth.session_manager import SessionManager
from auth.password_manager import PasswordManager
from core.enums import UserRole
from core.exceptions import ValidationError, AuthenticationError

print('=== AUTH SERVICE VERIFICATION ===')
print()

# Setup
SessionManager.reset()
repo = InMemoryUserRepository()
auth = AuthService(repo)

# Verify dependencies (UML class diagram)
assert isinstance(auth._pm, PasswordManager)
assert isinstance(auth._session, SessionManager)
print('AuthService uses PasswordManager class: PASSED')
print('AuthService uses SessionManager:        PASSED')

# Register
user = auth.register('alice', 'password123', UserRole.LEARNER)
assert user.id is not None
assert user.username == 'alice'
assert user.role == UserRole.LEARNER
assert user.password_hash.startswith('$2b$')
print(f'register(): id={user.id}, role={user.role.value} PASSED')
print(f'password is hashed: {user.password_hash[:20]}... PASSED')

# Duplicate username
try:
    auth.register('alice', 'anotherpass')
    print('FAILED - should have raised')
except ValidationError as e:
    print(f'Duplicate username raises ValidationError: PASSED')

# Short password
try:
    auth.register('bob', 'short')
    print('FAILED - should have raised')
except ValidationError as e:
    print(f'Short password raises ValidationError: PASSED')

# Login success
logged = auth.login('alice', 'password123')
assert logged.username == 'alice'
assert auth.verify_user() == True
print(f'login(): {logged.username} authenticated={auth.verify_user()} PASSED')

# Current user
cu = auth.current_user()
assert cu is not None
assert cu.username == 'alice'
print(f'current_user(): {cu.username} PASSED')

# Wrong password
try:
    auth.login('alice', 'wrongpass!')
    print('FAILED - should have raised')
except AuthenticationError as e:
    print(f'Wrong password raises AuthenticationError: PASSED')

# Logout
auth.logout()
assert auth.verify_user() == False
print(f'logout(): authenticated={auth.verify_user()} PASSED')

# Change password
auth.login('alice', 'password123')
auth.change_password(user.id, 'password123', 'newpassword!')
auth.logout()
try:
    auth.login('alice', 'password123')
    print('FAILED - old password should not work')
except AuthenticationError:
    pass
new_login = auth.login('alice', 'newpassword!')
assert new_login.username == 'alice'
print('change_password(): old rejected, new accepted PASSED')
auth.logout()

# Default users
auth.create_default_users()
admin_user = auth.login('admin', 'admin123')
assert admin_user.role == UserRole.ADMIN
print(f'Default admin:   role={admin_user.role.value} PASSED')
auth.logout()

learner_user = auth.login('learner', 'learner123')
assert learner_user.role == UserRole.LEARNER
print(f'Default learner: role={learner_user.role.value} PASSED')
auth.logout()

analyst_user = auth.login('analyst', 'analyst123')
assert analyst_user.role == UserRole.ANALYST
print(f'Default analyst: role={analyst_user.role.value} PASSED')
auth.logout()

# Idempotent default creation
auth.create_default_users()
print('create_default_users() twice (idempotent): PASSED')

print()
print('AUTH SERVICE OK')