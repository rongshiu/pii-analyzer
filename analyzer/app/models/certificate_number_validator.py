import re

def validate_certificate_number(cert: str) -> bool:
    # Remove spaces or hyphens if necessary
    cert = cert.strip()

    # Define patterns
    patterns = [
        r"^M000001[46]\d{4}$",   # MediKad
        r"^D000001[78]\d{4}$",   # Legasi
    ]

    return any(re.fullmatch(p, cert, re.IGNORECASE) for p in patterns)


# print(validate_certificate_number("M00000141234"))  # True
# print(validate_certificate_number("d00000181234"))  # True
# print(validate_certificate_number("123456"))        # False
# print(validate_certificate_number("X00000141234"))  # False
# print(validate_certificate_number("M00000151234"))  # False