import re

def validate_vietnam_id(id_number: str) -> bool:
    """
    Validates Vietnamese ID numbers:
    - CMND: 9 digits (old)
    - CCCD: 12 digits (new)
    """

    # Remove all non-digit characters (dashes, spaces, etc.)
    id_number = re.sub(r'\D', '', id_number)

    if len(id_number) == 9 and id_number.isdigit():
        return True  # CMND valid
    elif len(id_number) == 12 and id_number.isdigit():
        return validate_cccd_checksum(id_number)
    else:
        return False  # Invalid format

def validate_cccd_checksum(cccd: str) -> bool:
    # Placeholder validator: just checks format is 12 digits
    return True


# print(validate_vietnam_id("id is 101700203450"))