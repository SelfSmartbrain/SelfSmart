'''concept_extractor.py

Extracts candidate high‑level concepts from episodic and semantic memories.
Currently uses a simple keyword extraction based on TF‑IDF over the ``outcome`` field.
''' 

from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from ..memory.episodic_memory import EpisodicMemory
from ..memory.semantic_memory import SemanticMemory

class ConceptExtractor:
    def __init__(self, db_session, semantic_mem: SemanticMemory):
        self.db = db_session
        self.semantic_mem = semantic_mem
        self.vectorizer = TfidfVectorizer(max_features=20, stop_words='english')

    async def _fetch_outcomes(self) -> List[str]:
        from sqlalchemy import select
        stmt = select(EpisodicMemory).where(EpisodicMemory.outcome != None)
        result = await self.db.execute(stmt)
        episodes = result.scalars().all()
        return [ep.outcome for ep in episodes]

    async def extract(self) -> List[Dict[str, str]]:
        """Return a list of candidate concepts as ``{'term': str, 'score': float}``.
        
        This stub extracts the top TF‑IDF terms from recent outcomes.
        """
        texts = await self._fetch_outcomes()
        if not texts:
            return []
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        scores = tfidf_matrix.sum(axis=0).A1
        terms = self.vectorizer.get_feature_names_out()
        candidates = sorted(zip(terms, scores), key=lambda x: x[1], reverse=True)[:10]
        return [{"term": term, "score": float(score)} for term, score in candidates]
