import re

def validate_email(email: str) -> bool:
    """Validates an email address using a regex pattern."""
    email_regex = re.compile(
        r"^(?!.*\.\.)(?!.*\.$)[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    return bool(email_regex.match(email))