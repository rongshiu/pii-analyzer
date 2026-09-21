import re

def validate_vehicle_plate(plate: str) -> bool:
    plate = plate.strip().upper()

    patterns = [
        r"^[A-Z]{1,3}\d{1,4}[A-Z]?$",                    # Standard + Q-plates
        r"^(PUTRAJAYA|PROTON|PERDANA|WAJA)\s?\d{1,4}$",  # Named plates
        r"^Z[A-Z]{1,2}\d{1,4}$",                          # Military plates
    ]
    
    return any(re.fullmatch(p, plate) for p in patterns)

# print(validate_vehicle_plate("QAA671W"))  # True
# print(validate_vehicle_plate("WC2689R"))  # True