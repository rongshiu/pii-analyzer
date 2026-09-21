import re
from datetime import datetime

def validate_dob(text):
    month_names = r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|" \
                  r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    sep = r"[-/\s]"

    patterns = [
        rf"\b\d{{2,4}}{sep}(0?[1-9]|1[0-2]){sep}(0?[1-9]|[12][0-9]|3[01])\b",
        rf"\b(0?[1-9]|1[0-2]){sep}(0?[1-9]|[12][0-9]|3[01]){sep}\d{{2,4}}\b",
        rf"\b(0?[1-9]|[12][0-9]|3[01]){sep}(0?[1-9]|1[0-2]){sep}\d{{2,4}}\b",
        rf"\b\d{{2,4}}{sep}{month_names}{sep}(0?[1-9]|[12][0-9]|3[01])\b",
        rf"\b(0?[1-9]|[12][0-9]|3[01]){sep}{month_names}{sep}\d{{2,4}}\b",
        rf"\b{month_names}{sep}(0?[1-9]|[12][0-9]|3[01]){sep}\d{{2,4}}\b",
    ]

    formats = [
        "%Y-%m-%d", "%y-%m-%d", "%m-%d-%Y", "%m-%d-%y",
        "%d-%m-%Y", "%d-%m-%y", "%Y %b %d", "%y %b %d",
        "%d %B %Y", "%d %B %y", "%B %d %Y", "%b %d %y",
        "%Y/%m/%d", "%y/%m/%d", "%m/%d/%Y", "%m/%d/%y",
        "%d/%m/%Y", "%d/%m/%y", "%Y %m %d", "%d %m %Y"
    ]

    today = datetime.today()

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            date_str = match.group()
            for fmt in formats:
                try:
                    parsed = datetime.strptime(date_str, fmt)

                    # Normalize 2-digit years
                    if parsed.year < 100:
                        parsed = parsed.replace(year=parsed.year + 1900 if parsed.year > today.year % 100 else parsed.year + 2000)

                    # Reject future dates
                    if parsed > today:
                        continue

                    # Validate age range: 0 to 120 years
                    age = (today - parsed).days / 365.25
                    if 0 <= age <= 120:
                        return True

                except ValueError:
                    continue

    return False

