import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Validation layer to filter out low-quality or poisoned training data.
    Implements Fix #5.
    """

    def __init__(self, min_length: int = 100, max_length: int = 10000):
        self.min_length = min_length
        self.max_length = max_length

        # Simple spam/poisoning patterns
        self.poison_patterns = [
            r"buy now", r"special offer", r"click here", # Marketing/SEO
            r"copyright.*all rights reserved",          # Legal fluff
            r"\[edit\]", r"edit source",                # Wiki boilerplate
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"      # IP addresses (potentially sensitive)
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.poison_patterns]

    def validate_content(self, content: str) -> float:
        """
        Scores content quality from 0.0 to 1.0.
        Returns 0.0 if the content should be discarded.
        """
        if not content or len(content) < self.min_length:
            return 0.0

        if len(content) > self.max_length:
            return 0.0

        score = 1.0

        # Check for poison patterns
        matches = 0
        for pattern in self.compiled_patterns:
            if pattern.search(content):
                matches += 1

        # Penalize score based on matches
        score -= (matches * 0.2)

        # Check for repetition (potential AI hallucination or spam)
        words = content.split()
        if len(words) > 50:
            unique_words_ratio = len(set(words)) / len(words)
            if unique_words_ratio < 0.4:  # Too much repetition
                score -= 0.5

        return max(0.0, score)

    def filter_batch(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters a list of potential training samples."""
        valid_samples = []
        for item in data_list:
            content = item.get("content", "")
            quality = self.validate_content(content)
            if quality > 0.5:
                item["quality_score"] = quality
                valid_samples.append(item)

        logger.info(f"Validated batch: {len(valid_samples)}/{len(data_list)} samples passed.")
        return valid_samples
