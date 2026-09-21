import re

def validate_password(password: str, min_length: int = 8, max_length: int = 128) -> bool:
    """
    Validate password strength.
    Requirements (default):
    - Length between min_length and max_length
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&* etc.)
    - No spaces
    """
    if not (min_length <= len(password) <= max_length):
        return False

    pattern = re.compile(
        r"^(?=.*[a-z])"      # At least one lowercase letter
        r"(?=.*[A-Z])"       # At least one uppercase letter
        r"(?=.*\d)"          # At least one digit
        r"(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?])"  # At least one special character
        r"[^\s]+$"           # No spaces allowed
    )

    return bool(pattern.match(password))
