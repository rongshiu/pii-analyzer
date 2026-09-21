import re

def luhn_checksum(card_number: str) -> bool:
    card_number = re.sub(r"[^\d]", "", card_number)
    total = 0
    reverse_digits = card_number[::-1]

    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n

    return total % 10 == 0


def get_card_type(card_number: str) -> str:
    card_number = re.sub(r"[^\d]", "", card_number)  # Remove non-digit characters
    card_types = {
        "Visa": r"^4\d{12}(\d{3})?$",  # 13 or 16 digits
        "MasterCard": r"^5[1-5]\d{14}$",  # Starts with 51-55
        "American Express": r"^3[47]\d{13}$",  # Starts with 34 or 37
        "Discover": r"^6(?:011|5\d{2})\d{12}$",  # Starts with 6011 or 65
        "JCB": r"^(?:2131|1800|35\d{3})\d{11}$",
        "Diners Club": r"^3(?:0[0-5]|[68]\d)\d{11}$",
        "Maestro": r"^(5018|5020|5038|56|57|58|6304|6759|676[1-3])\d{8,15}$",
        "Verve": r"^(5060|5061|5078|5079|6500)\d{12,15}$"
    }

    for card_type, pattern in card_types.items():
        if re.match(pattern, card_number):
            return card_type
    return "Unknown"


def validate_credit_card(card_number: str) -> bool:
    card_type = get_card_type(card_number)
    is_valid = luhn_checksum(card_number)
    return is_valid and card_type != "Unknown"

# print(validate_credit_card("4539148803436467"))