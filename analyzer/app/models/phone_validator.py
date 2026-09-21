import re

def validate_phone_number(phone: str) -> bool:
    phone = phone.strip().replace(" ", "").replace("-", "")

    patterns = [
        # Malaysia
        r"^\+?60(1[0-46-9]\d{7,8}|[3-9]\d{7,8})$",   # Mobile (011 can have 8 digits), landlines (3-9)
        r"^0(1[0-46-9]\d{7,8}|[3-9]\d{7,8})$",

        # Indonesia
        r"^\+?62(8\d{8,10}|[2-9]\d{7,9})$",   # Mobile starts with 8, landlines with 2-9
        r"^0(8\d{8,10}|[2-9]\d{7,9})$",

        # Thailand
        r"^\+?66([689]\d{8}|[2-5]\d{7})$",   # Mobile starts with 6, 8, or 9; landline 2–5
        r"^0([689]\d{8}|[2-5]\d{7})$",

        # Vietnam
        r"^\+?84([3-9]\d{8}|2\d{9})$",   # Mobile starts 3–9, landline starts with 2
        r"^0([3-9]\d{8}|2\d{9})$",

        # Singapore
        r"^\+?65([689]\d{7})$",   # Mobile & landlines start with 6, 8, or 9
        r"^([689]\d{7})$",

        # India
        r"^\+?91[6-9]\d{9}$",   # Mobile
        r"^0[1-9]\d{9}$",       # Landlines

        # US
        r"^\+?1\d{10}$",        # With country code
        r"^\(?\d{3}\)?\d{7}$",  # Landlines

        # UK
        r"^\+?44\d{10}$",       # With country code
        r"^0\d{10}$",           # Standard national format
    ]

    for pattern in patterns:
        if re.fullmatch(pattern, phone):
            return True

    return False

# print(validate_phone_number("98765432"))