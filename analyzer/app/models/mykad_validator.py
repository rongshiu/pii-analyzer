import re
from datetime import datetime

def validate_mykad(ic_number):
    # Pre-compiled regex pattern for MyKad validation (with optional dashes)
    mykad_pattern = re.compile(r"\b(?!000000)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])[-]?\d{2}[-]?\d{4}\b")
    # Valid state codes
    valid_state_codes = {
        # Johor
        "01", "21", "22", "23", "24",
        # Kedah
        "02", "25", "26", "27",
        # Kelantan
        "03", "28", "29",
        # Melaka
        "04", "30",
        # Negeri Sembilan
        "05", "31", "59",
        # Pahang
        "06", "32", "33",
        # Pulau Pinang
        "07", "34", "35",
        # Perak
        "08", "36", "37", "38", "39",
        # Perlis
        "09", "40",
        # Selangor
        "10", "41", "42", "43", "44",
        # Terengganu
        "11", "45", "46",
        # Sabah
        "12", "47", "48", "49",
        # Sarawak
        "13", "50", "51", "52", "53",
        # Wilayah Persekutuan (Kuala Lumpur)
        "14", "54", "55", "56", "57",
        # Wilayah Persekutuan (Labuan)
        "15", "58",
        # Wilayah Persekutuan (Putrajaya)
        "16",
        # Negeri Tidak Diketahui
        "82"
    }


    # Match the general MyKad format using the regex
    match = mykad_pattern.match(ic_number)
    
    if not match:
        return False  # Invalid format
    
    # Remove dashes for consistent processing
    ic_number_cleaned = ic_number.replace("-", "")
    
    # Extract the birth date and state code parts
    birth_str = ic_number_cleaned[:6]
    state_code = ic_number_cleaned[6:8]
    serial_number = ic_number_cleaned[8:]
    
    # Validate the state code (should be valid according to the defined set)
    if state_code not in valid_state_codes:
        return False
    
    # Validate the serial number (should be a 4-digit number between 0000-9999)
    if not serial_number.isdigit() or len(serial_number) != 4:
        return False
    
    # Validate the birth date to check if it's a valid date
    try:
        datetime.strptime(birth_str, "%y%m%d")
    except ValueError:
        return False  # Invalid date (e.g., 32nd of a month, leap year issues)
    
    return True
