import re

def validate_thailand_id(text: str) -> bool:
    """
    Validates a Thailand National ID number.
    
    Accepts formats like:
    - '1101700203450'
    - '1-1017-00203-45-0'
    - '1 1017 00203 45 0'
    
    Returns:
        True if the ID is valid according to the checksum.
    """
    # Remove all non-digit characters (like dashes, spaces)
    id_number = re.sub(r"\D", "", text)

    # Must be exactly 13 digits
    if len(id_number) != 13 or not id_number.isdigit():
        return False

    # Calculate checksum
    weight = list(range(13, 1, -1))  # 13 to 2
    total = sum(int(d) * w for d, w in zip(id_number[:12], weight))
    checksum = (11 - (total % 11)) % 10

    return checksum == int(id_number[12])


# print(validate_thailand_id("id is 1-101700203450"))
# print(validate_thailand_id("id is 1-2011-98765-00-0"))
