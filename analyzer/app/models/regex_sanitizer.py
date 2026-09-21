# app/models/regex_sanitizer.py
import re
from datetime import datetime

from app.schema.presidio_schema import PIIDetectData
from app.models.mykad_validator import validate_mykad
from app.models.nik_validator import validate_indonesia_nik
from app.models.thai_id_validator import validate_thailand_id
from app.models.vietnam_id_validator import validate_vietnam_id
from app.models.password_validator import validate_password
from app.models.swift_validator import validate_swift
from app.models.passport_validator import validate_passport
from app.models.phone_validator import validate_phone_number
from app.models.policy_number_validator import validate_policy_number
from app.models.certificate_number_validator import validate_certificate_number
from app.models.vehicle_plate_validator import validate_vehicle_plate
from app.models.credit_card_validator import validate_credit_card
from app.utility.logger import get_logger

logger = get_logger()

class RegexSanitizer:
    # def __init__(self, address_model: HuggingFaceAddressRecognizer):
    #     self._address_model = address_model

    def replace_credit_card(self, text, label="CREDIT_CARD") -> list[PIIDetectData]:
        pattern = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
        results = []
        for match in pattern.finditer(text):
            if validate_credit_card(match.group()):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=match.group(),
                        score=0.95,
                    )
                )
        return results

    def replace_mykad(self, text, label="MYKAD") -> list[PIIDetectData]:
        pattern = re.compile(r"\b\d{12}\b|\b\d{6}-\d{2}-\d{4}\b")
        results = []
        for match in pattern.finditer(text):
            if validate_mykad(match.group()):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=match.group(),
                        score=0.95,
                    )
                )
        return results

    def replace_nik(self, text, label="INDONESIAN_NIK") -> list[PIIDetectData]:
        pattern = re.compile(r"(?<!\d-)\b\d{16}\b")
        results = []
        for match in pattern.finditer(text):
            if validate_indonesia_nik(match.group()):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=match.group(),
                        score=0.95,
                    )
                )
        return results
    
    def replace_thai_id(self, text, label="THAILAND_ID") -> list[PIIDetectData]:
        pattern = re.compile(r"(?<!\d)(\d{1}-\d{4}-\d{5}-\d{2}-\d{1}|\d{13})(?!\d)")
        results = []
        for match in pattern.finditer(text):
            if validate_thailand_id(match.group()):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=match.group(),
                        score=0.95,
                    )
                )
        return results
    
    def replace_vietnam_id(self, text, label="VIETNAM_ID") -> list[PIIDetectData]:
        pattern = re.compile(r"(?<!\d-)\b\d{12}\b")
        results = []
        for match in pattern.finditer(text):
            if validate_vietnam_id(match.group()):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=match.group(),
                        score=0.95,
                    )
                )
        return results

    def replace_swift(self, text, label="SWIFT_CODE") -> list[PIIDetectData]:
        pattern = re.compile(r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b")
        results = []
        # logger.info(f"text: {text}")
        for match in pattern.finditer(text):
            # logger.info(f"Found potential SWIFT code: {match.group()}")
            if validate_swift(match.group()):
                # logger.info(f"Matched SWIFT code: {match.group()}")
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=match.group(),
                        score=0.95,
                    )
                )
        return results

    def replace_passport(self, text, label="PASSPORT") -> list[PIIDetectData]:
        pattern = re.compile(
            r"\b("
            r"\d{9}"
            r"|[A-Z]\d{7}"
            r"|[A-Z]{2}\d{7}"
            r"|[A-Z]{2}\d{6}"
            r"|[A-Z]\d{8}"
            r"|[A-Z]{1,2}\d{7}"
            r"|[A-Z]\d{6}"
            r"|[A-Z0-9]{8,9}"
            r")\b",
            re.IGNORECASE
        )
        results = []
        for match in pattern.finditer(text):
            if validate_passport(match.group()):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=match.group(),
                        score=0.95,
                    )
                )
        return results

    def replace_password(self, text, label="PASSWORD") -> list[PIIDetectData]:
        # pattern = re.compile(
        #     r"\b(?=\S{8,128})(?=.*[a-z])(?=.*[A-Z])(?=.*\d)"
        #     r"(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?])[^\s]{8,128}\b"
        # )
        pattern = re.compile(
            r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)"
            r"(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?])"
            r"[^\s]{8,128}"
        )
        results = []
        for match in pattern.finditer(text):
            if validate_password(match.group()):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=match.group(),
                        score=0.95,
                    )
                )
        return results

    def replace_phone_number(self, text, label="PHONE_NUMBER") -> list[PIIDetectData]:
        pattern = re.compile(r"(?<![A-Za-z0-9])\+?\d[\d\s\-]{6,20}\d(?![A-Za-z0-9])")
        results = []
        for match in pattern.finditer(text):
            candidate = match.group()
            if validate_phone_number(candidate):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=candidate,
                        score=0.85,
                    )
                )
        return results

    def replace_policy_number(self, text, label="POLICY_NUMBER") -> list[PIIDetectData]:
        pattern = re.compile(r"\bTMKT\d{8}\b", re.IGNORECASE)
        results = []
        for match in pattern.finditer(text):
            candidate = match.group()
            if validate_policy_number(candidate):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=candidate,
                        score=0.9,
                    )
                )
        return results

    def replace_certificate_number(self, text, label="CERTIFICATE_NUMBER") -> list[PIIDetectData]:
        pattern = re.compile(r"\b[MD]\d{8}\d{4}\b", re.IGNORECASE)
        results = []
        for match in pattern.finditer(text):
            candidate = match.group()
            if validate_certificate_number(candidate):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=candidate,
                        score=0.9,
                    )
                )
        return results

    def replace_vehicle_plate(self, text, label="VEHICLE_PLATE") -> list[PIIDetectData]:
        pattern = re.compile(
            r"\b(?:"
            r"[A-Z]{1,3}\d{1,4}[A-Z]?|"
            r"PUTRAJAYA\s?\d{1,4}|"
            r"PROTON\s?\d{1,4}|"
            r"PERDANA\s?\d{1,4}|"
            r"WAJA\s?\d{1,4}|"
            r"Z[A-Z]{1,2}\d{1,4}"
            r")\b"
        )
        results = []
        for match in pattern.finditer(text):
            candidate = match.group()
            if validate_vehicle_plate(candidate):
                results.append(
                    PIIDetectData(
                        data_element=label,
                        start=match.start(),
                        end=match.end(),
                        pii_text=candidate,
                        score=0.9,
                    )
                )
        return results