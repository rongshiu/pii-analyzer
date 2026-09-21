# app/services/pii_detect.py
import os
import sys
from pathlib import Path

# Now safe to import presidio modules
from presidio_analyzer import AnalyzerEngine, RecognizerResult, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from app.models.regex_sanitizer import RegexSanitizer
from app.schema.presidio_schema import PIIDetectData, PIIDetectDataCsv
from app.utility.logger import get_logger
from app.models.address_recognizer import HuggingFaceAddressRecognizer

import presidio_analyzer.recognizer_registry.recognizers_loader_utils as recognizer_utils

logger = get_logger()

class PIIDetectService:
    def __init__(self, address_model: HuggingFaceAddressRecognizer):
        logger.info("[PIIDetectService] Starting init")

        is_local = os.getenv("IS_LOCAL", "false").lower() == "true"
        logger.info(f"[PIIDetectService] IS_LOCAL={is_local} → loading spaCy {'automatically' if is_local else 'manually'}")

        if is_local:
            spacy_model_path = "en_core_web_lg"
            registry = None
        else:
            base_path = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent
            spacy_model_path = str(base_path / "_internal" / "app" / "en_core_web_lg")
            logger.info(f"[PIIDetectService] Using spaCy model path: {spacy_model_path}")

            default_config_path = base_path / "presidio_analyzer" / "conf" / "default_recognizers.yaml"
            recognizer_utils.RecognizerConfigurationLoader._get_full_conf_path = staticmethod(lambda: default_config_path)
            logger.info(f"[PIIDetectService] Patched Presidio default recognizer config path: {default_config_path}")

            registry = RecognizerRegistry()
            registry.load_predefined_recognizers()
            logger.info("[PIIDetectService] RecognizerRegistry initialized with patched path.")

        config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": spacy_model_path}]
        }
        provider = NlpEngineProvider(nlp_configuration=config)
        nlp_engine = provider.create_engine()

        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)
        logger.info("[PIIDetectService] AnalyzerEngine initialized.")

        self._anonymizer = AnonymizerEngine()
        self._regex_sanitizer = RegexSanitizer()
        self._address_model = address_model
        self._entities = ["PERSON", "EMAIL_ADDRESS", "IP_ADDRESS", "IBAN_CODE"]

    def regex_detection(self, text: str, allowed_elements: list[str] = None) -> list[PIIDetectData]:
        allowed_elements = set(allowed_elements or [])
        results = []
        # logger.info(f"[PIIDetectService] Running regex detection for elements: {allowed_elements}")

        regex_map = {
            "MYKAD": self._regex_sanitizer.replace_mykad,
            "INDONESIAN_NIK": self._regex_sanitizer.replace_nik,
            "THAILAND_ID": self._regex_sanitizer.replace_thai_id,
            "CREDIT_CARD": self._regex_sanitizer.replace_credit_card,
            "PHONE_NUMBER": self._regex_sanitizer.replace_phone_number,
            "VIETNAM_ID": self._regex_sanitizer.replace_vietnam_id,
            "SWIFT_CODE": self._regex_sanitizer.replace_swift,
            "PASSPORT": self._regex_sanitizer.replace_passport,
            "PASSWORD": self._regex_sanitizer.replace_password,
            "VEHICLE_PLATE": self._regex_sanitizer.replace_vehicle_plate,
            "CERTIFICATE_NUMBER": self._regex_sanitizer.replace_certificate_number,
            "POLICY_NUMBER": self._regex_sanitizer.replace_policy_number
        }

        for key, func in regex_map.items():
            if key in allowed_elements:
                results.extend(func(text))

        return results

    def analyse_text(self, text: str, allowed_data_elements: list[str], include_address: bool = False) -> list[PIIDetectData]:
        return_results = []

        regex_results = self.regex_detection(text, allowed_elements=allowed_data_elements)
        return_results.extend(regex_results)

        anonymized_text = text
        if regex_results:
            regex_presidio_results = [
                RecognizerResult(pii.data_element, pii.start, pii.end, pii.score)
                for pii in regex_results
            ]
            anonymized_text = self._anonymizer.anonymize(text=text, analyzer_results=regex_presidio_results).text

        if include_address and "ADDRESS" in allowed_data_elements:
            address_results = self._address_model.analyze(anonymized_text)
            return_results.extend([
                PIIDetectData(
                    data_element=addr["data_element"],
                    start=addr["start"],
                    end=addr["end"],
                    pii_text=anonymized_text[addr["start"]:addr["end"]],
                    score=addr["score"]
                ) for addr in address_results if addr["score"] == 1.0
            ])
            all_results = [
                RecognizerResult(pii.data_element, pii.start, pii.end, pii.score)
                for pii in return_results
            ]
            anonymized_text = self._anonymizer.anonymize(text=anonymized_text, analyzer_results=all_results).text

        presidio_results = self._analyzer.analyze(
            text=anonymized_text,
            entities=allowed_data_elements,
            language="en"
        )

        for result in presidio_results:
            if result.score > 0.5:
                return_results.append(
                    PIIDetectData(
                        data_element=result.entity_type,
                        start=result.start,
                        end=result.end,
                        pii_text=anonymized_text[result.start:result.end],
                        score=result.score
                    )
                )

        return return_results

    def analyse_text_csv(
        self,
        text_list: list,
        column_name: str,
        chunk_index: int,
        allowed_data_elements: list[str],
        include_address: bool = False
    ) -> list[PIIDetectDataCsv]:
        return_results = []

        for text_entry in text_list:
            text = text_entry.input_text
            chunk_results = []

            # regex
            regex_results = self.regex_detection(text=text, allowed_elements=allowed_data_elements)
            chunk_results.extend([
                PIIDetectDataCsv(
                    data_element=pii.data_element,
                    column_name=column_name,
                    chunk_index=chunk_index,
                    start=pii.start,
                    end=pii.end,
                    pii_text=pii.pii_text,
                    score=pii.score,
                ) for pii in regex_results
            ])

            anonymized_text = text
            if regex_results:
                regex_presidio_results = [
                    RecognizerResult(pii.data_element, pii.start, pii.end, pii.score)
                    for pii in regex_results
                ]
                anonymized_text = self._anonymizer.anonymize(text=text, analyzer_results=regex_presidio_results).text

            if include_address and "ADDRESS" in allowed_data_elements:
                address_results = self._address_model.analyze(anonymized_text)
                for addr in address_results:
                    if addr["score"] == 1.0:
                        chunk_results.append(
                            PIIDetectDataCsv(
                                data_element=addr["data_element"],
                                column_name=column_name,
                                chunk_index=chunk_index,
                                start=addr["start"],
                                end=addr["end"],
                                pii_text=anonymized_text[addr["start"]:addr["end"]],
                                score=addr["score"]
                            )
                        )
                all_results = [
                    RecognizerResult(pii.data_element, pii.start, pii.end, pii.score)
                    for pii in chunk_results
                ]
                anonymized_text = self._anonymizer.anonymize(text=anonymized_text, analyzer_results=all_results).text

            presidio_results = self._analyzer.analyze(
                text=anonymized_text,
                entities=allowed_data_elements,
                language="en"
            )

            for result in presidio_results:
                if result.score > 0.5:
                    chunk_results.append(
                        PIIDetectDataCsv(
                            data_element=result.entity_type,
                            column_name=column_name,
                            chunk_index=chunk_index,
                            start=result.start,
                            end=result.end,
                            pii_text=anonymized_text[result.start:result.end],
                            score=result.score
                        )
                    )

            return_results.extend(chunk_results)

        return return_results
