import re
from datetime import datetime

def validate_indonesia_nik(text):
    """
    Extracts and validates Indonesian NIKs from text.
    NIK format:
      - 16 digits
      - Birthdate is in DDMMYY format (with +40 to DD for female)
      - Valid province code (first 2 digits)
    Supports optional dashes.
    Returns True if any valid NIK found, else False.
    """

    pattern = re.compile(r'\b(?:\d{16}|\d{2}-\d{4}-\d{6}-\d{4})\b')

    province_codes = {
        "11": "Aceh (NAD)",
        "12": "North Sumatra",
        "13": "West Sumatra",
        "14": "Riau",
        "15": "Jambi",
        "16": "South Sumatra",
        "17": "Bengkulu",
        "18": "Lampung",
        "19": "Bangka Belitung Islands",
        "21": "Riau Islands",
        "31": "DKI Jakarta",
        "32": "West Java",
        "33": "Central Java",
        "34": "DI Yogyakarta",
        "35": "East Java",
        "36": "Banten",
        "51": "Bali",
        "52": "West Nusa Tenggara (NTB)",
        "53": "East Nusa Tenggara (NTT)",
        "61": "West Kalimantan",
        "62": "Central Kalimantan",
        "63": "South Kalimantan",
        "64": "East Kalimantan",
        "65": "North Kalimantan",
        "71": "North Sulawesi",
        "72": "Central Sulawesi",
        "73": "South Sulawesi",
        "74": "Southeast Sulawesi",
        "75": "Gorontalo",
        "76": "West Sulawesi",
        "81": "Maluku",
        "82": "North Maluku",
        "91": "Papua",
        "92": "West Papua",
        "93": "South Papua",
        "94": "Central Papua",
        "95": "Mountains Papua"
    }

    valid_province_codes = set(province_codes.keys())

    for match in pattern.findall(text):
        nik = match.replace("-", "")
        if not re.fullmatch(r"\d{16}", nik):
            continue

        province_code = nik[:2]
        if province_code not in valid_province_codes:
            continue

        dd = int(nik[6:8])
        mm = nik[8:10]
        yy = nik[10:12]

        # Adjust DD if encoded for female
        if dd > 40:
            dd -= 40

        try:
            datetime.strptime(f"{dd:02}{mm}{yy}", "%d%m%y")
        except ValueError:
            continue

        return True  # Valid NIK found

    return False  # No valid NIKs

# print(validate_indonesia_nik("id is 7105074205820001"))