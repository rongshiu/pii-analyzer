import re

def validate_passport(passport_number: str) -> bool:
    """
    Validates passport numbers for multiple countries based on known format patterns.
    """

    passport_number = passport_number.strip().upper()

    patterns = [
        r"^\d{9}$",                     # USA, UK
        r"^[A-Z]\d{7}$",                # India, Australia, Singapore, Indonesia (7-digit variant)
        r"^[A-Z]{2}\d{7}$",             # Germany
        r"^[A-Z]{2}\d{6}$",             # Canada
        r"^[A-Z]\d{8}$",                # Vietnam (9-char)
        r"^[A-Z]{1,2}\d{7}$",           # Thailand (e.g., TA1234567)
        r"^[A-Z]\d{6}$",                # Indonesia (6-digit variant)
        r"^[AHKM]\d{8}$",               # Malaysia 
    ]

    for pattern in patterns:
        if re.fullmatch(pattern, passport_number):
            return True

    return False
