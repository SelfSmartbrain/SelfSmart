'''concept_merger.py

Merges overlapping or duplicate concepts detected by the extractor.
Simplified implementation uses string similarity (Levenshtein distance) to decide merges.
''' 

import difflib
from typing import List, Dict

class ConceptMerger:
    def __init__(self, similarity_threshold: float = 0.8):
        self.threshold = similarity_threshold

    def _similar(self, a: str, b: str) -> bool:
        return difflib.SequenceMatcher(None, a, b).ratio() >= self.threshold

    def merge(self, concepts: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Merge concepts list, combining scores of similar terms.
        
        Returns a new list of merged concepts.
        """
        merged = []
        for cand in concepts:
            term = cand["term"]
            score = cand["score"]
            found = False
            for m in merged:
                if self._similar(term, m["term"]):
                    m["score"] += score
                    found = True
                    break
            if not found:
                merged.append({"term": term, "score": score})
        return merged
