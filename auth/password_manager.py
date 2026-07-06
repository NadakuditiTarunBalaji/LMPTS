"""
password_manager.py
-------------------
Handles all password hashing and verification using bcrypt.

UML Class Diagram:
    ┌──────────────────────┐
    │   PasswordManager    │
    ├──────────────────────┤
    │ hash_password()      │
    │ verify_password()    │
    │ generate_salt()      │
    └──────────────────────┘

UML: Shown as a class in the class diagram.
     AuthService has a dependency arrow (--->) to PasswordManager.

UML Sequence Diagram (Section 5):
    Step 6: AuthService calls PasswordManager.verify_password()

Install: pip install bcrypt
"""

import bcrypt


class PasswordManager:
    """
    Handles bcrypt password operations.

    UML Class Diagram: PasswordManager class with three methods.

    Why bcrypt?
        - Adaptive cost factor makes brute-force slow
        - Salt is embedded in the hash — no separate storage
        - Industry standard for password storage

    Usage:
        pm = PasswordManager()
        hashed = pm.hash_password("admin123")
        pm.verify_password("admin123", hashed)  → True
    """

    @staticmethod
    def generate_salt() -> bytes:
        """
        Generate a cryptographically random salt.

        Typically not called directly — hash_password() handles
        salt generation internally.

        Returns:
            bytes: A bcrypt salt containing cost factor and random bytes.

        Example:
            salt = PasswordManager.generate_salt()
            # b'$2b$12$someRandomBytesHere...'
        """
        return bcrypt.gensalt()

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """
        Hash a plain-text password using bcrypt.

        UML Sequence Diagram (Section 5):
            AuthService.register() → PasswordManager.hash_password()

        Process:
            1. Encode string to UTF-8 bytes
            2. Generate random salt (cost factor 12)
            3. Compute bcrypt hash
            4. Return as UTF-8 string for database storage

        Args:
            plain_password: The user's plain-text password.

        Returns:
            str: bcrypt hash starting with "$2b$12$..."

        Raises:
            ValueError: If plain_password is empty.

        Example:
            hashed = PasswordManager.hash_password("admin123")
            # "$2b$12$A8rKsomethingLong..."
        """
        if not plain_password:
            raise ValueError("Cannot hash an empty password")

        hashed_bytes = bcrypt.hashpw(
            plain_password.encode("utf-8"),
            bcrypt.gensalt(),
        )
        return hashed_bytes.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Check whether a plain-text password matches a stored hash.

        UML Sequence Diagram (Section 5):
            Step 6: PasswordManager.verify_password()
            Returns True → session created
            Returns False → AuthenticationError raised

        bcrypt.checkpw extracts the salt from the hash, re-computes,
        and compares in constant time (safe against timing attacks).

        Args:
            plain_password  : Password the user just typed.
            hashed_password : Hash retrieved from database.

        Returns:
            True  if the password is correct.
            False if it does not match.

        Example:
            PasswordManager.verify_password("admin123", stored_hash)
        """
        if not plain_password or not hashed_password:
            return False

        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False