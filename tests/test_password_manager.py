from auth.password_manager import PasswordManager

print('=== PASSWORD MANAGER VERIFICATION ===')
print()

pm = PasswordManager()
print(f'PasswordManager instance: {pm}')

# Verify it is a class (UML requirement)
assert isinstance(pm, PasswordManager)
print('PasswordManager is a class: PASSED')

# Static methods accessible both ways
h1 = pm.hash_password('admin123')
h2 = PasswordManager.hash_password('admin123')
print(f'Instance call:    {h1[:30]}...')
print(f'Class call:       {h2[:30]}...')
assert h1.startswith('$2b$')
assert h2.startswith('$2b$')
print('Both calls produce bcrypt hash: PASSED')

# Hashes are different each call (different salts)
assert h1 != h2
print('Different hash each call (unique salts): PASSED')

# Verify correct password
assert pm.verify_password('admin123', h1) == True
print('verify_password correct: True PASSED')

# Verify wrong password
assert pm.verify_password('wrongpass', h1) == False
print('verify_password wrong: False PASSED')

# Verify empty inputs
assert pm.verify_password('', h1) == False
assert pm.verify_password('admin123', '') == False
print('verify_password empty inputs: False PASSED')

# Hash empty raises
try:
    pm.hash_password('')
    print('FAILED - should have raised')
except ValueError as e:
    print(f'hash_password empty raises ValueError: PASSED')

# generate_salt
salt = pm.generate_salt()
assert isinstance(salt, bytes)
print(f'generate_salt() returns bytes: {salt[:20]}... PASSED')

# Salts are unique
s1 = pm.generate_salt()
s2 = pm.generate_salt()
assert s1 != s2
print('generate_salt() unique each call: PASSED')

print()
print('PASSWORD MANAGER OK')
