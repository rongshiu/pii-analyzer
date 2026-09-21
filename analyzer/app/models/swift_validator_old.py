# app/models/swift_validator.py
import re

# ISO 3166-1 alpha-2 country codes
VALID_COUNTRY_CODES = {
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ",
    "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS",
    "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
    "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE",
    "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF", "GG",
    "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GT", "GU", "GW", "GY", "HK", "HM", "HN", "HR",
    "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", "JE", "JM", "JO", "JP",
    "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK",
    "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK", "ML", "MM",
    "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NC", "NE",
    "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK",
    "PL", "PM", "PN", "PR", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW", "SA", "SB", "SC",
    "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS", "ST", "SV", "SX",
    "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TV",
    "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI", "VN", "VU", "WF", "WS",
    "YE", "YT", "ZA", "ZM", "ZW"
}

def validate_swift(swift_code: str) -> bool:
    """
    Strictly validate a SWIFT/BIC code:
    - 8 or 11 characters only
    - Format: 4 uppercase letters (bank) + 2 uppercase letters (country) + 2 uppercase letters/digits (location) + optional 3 uppercase letters/digits (branch)
    - Validate that the 2-letter country code is in ISO 3166-1 alpha-2
    """
    swift_code = swift_code.strip()

    if len(swift_code) not in (8, 11):
        return False

    bank = swift_code[0:4]
    country = swift_code[4:6]
    location = swift_code[6:8]
    branch = swift_code[8:] if len(swift_code) == 11 else None

    if not re.fullmatch(r"[A-Z]{4}", bank):
        return False
    if not re.fullmatch(r"[A-Z]{2}", country) or country not in VALID_COUNTRY_CODES:
        return False
    if not re.fullmatch(r"[A-Z0-9]{2}", location):
        return False
    if branch and not re.fullmatch(r"[A-Z0-9]{3}", branch):
        return False

    return True


# print(validate_swift("RHBBMYKL123"))