import os
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from app.utility.logger import get_logger

logger = get_logger()

class HuggingFaceAddressRecognizer:
    def __init__(self, cache_dir, model_name_or_path=os.getenv("HF_ADDRESS_MODEL", "org/address-detector")):
        self.HF_TOKEN = os.getenv("HF_TOKEN")
        if not self.HF_TOKEN:
            logger.warning("Hugging Face token not found in environment. Private models may fail to load.")

        logger.info(f"Loading model from: {model_name_or_path}")
        
        offline = os.getenv("TRANSFORMERS_OFFLINE", "0") == "1"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, token=self.HF_TOKEN, cache_dir=cache_dir,  local_files_only=offline)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name_or_path, token=self.HF_TOKEN, cache_dir=cache_dir,  local_files_only=offline)

        self.ner_pipeline = pipeline(
            "ner",
            model=self.model,
            tokenizer=self.tokenizer,
            aggregation_strategy="simple",
            device=-1  # CPU only
        )
        logger.info("NER pipeline initialized successfully.")

    def analyze(self, text: str):
        # logger.debug(f"Analyzing text: {text}")
        raw_entities = self.ner_pipeline(text)
        # logger.debug(f"Raw NER entities: {raw_entities}")

        results = []
        current_group = []

        for entity in raw_entities:
            if entity["entity_group"] != "ADDRESS":
                continue

            if current_group and entity["start"] > current_group[-1]["end"] + 1:
                grouped_result = self._format_group(current_group, text)
                results.append(grouped_result)
                # logger.debug(f"Grouped address: {grouped_result}")
                current_group = []

            current_group.append(entity)

        if current_group:
            grouped_result = self._format_group(current_group, text)
            results.append(grouped_result)
            # logger.debug(f"Grouped address: {grouped_result}")

        logger.info(f"Detected {len(results)} address(es).")
        return results

    def _format_group(self, group, text):
        start = group[0]["start"]
        end = group[-1]["end"]
        score = sum(e["score"] for e in group) / len(group)
        span_text = text[start:end].strip()

        return {
            "data_element": "ADDRESS",
            "start": start,
            "end": end,
            "pii_text": span_text,
            "score": round(score, 3)
        }
