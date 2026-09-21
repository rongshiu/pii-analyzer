import re

def validate_policy_number(policy: str) -> bool:
    pattern = r"^TMKT\d{8}$"
    return bool(re.fullmatch(pattern, policy.strip(), re.IGNORECASE))

# print(validate_policy_number("TMKT12345678"))  # True
# print(validate_policy_number("tmkt12345678"))  # False (case-sensitive)
# print(validate_policy_number("TMKT1234"))      # False
# print(validate_policy_number("TMK12345678"))   # False

