"""Knowledge Gap Detector."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.knowledge_graph.reasoning import KnowledgeGraphReasoner
from src.rag.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)


class KnowledgeGapDetector:
    """Analyzes knowledge base coverage to detect missing concepts and weak domains."""

    def __init__(
        self,
        kg_reasoner: KnowledgeGraphReasoner,
        vector_store: VectorStoreManager,
    ) -> None:
        self.kg_reasoner = kg_reasoner
        self.vector_store = vector_store

    async def detect_gaps(self, domain: str | None = None) -> list[dict[str, Any]]:
        """
        Scan the knowledge graph and vector store to detect knowledge gaps.
        Returns a list of gap dictionaries:
        {
            "gap_id": "...",
            "domain": "...",
            "importance": 0.92,
            "confidence": 0.31,
            "description": "..."
        }
        """
        logger.info(f"Detecting knowledge gaps for domain: {domain or 'ALL'}")
        gaps = []
        
        # 1. Graph-based gap detection
        missing_prereqs = await self.kg_reasoner.find_missing_prerequisites()
        for prereq in missing_prereqs:
            gaps.append({
                "domain": domain or "general",
                "description": f"Missing prerequisite: {prereq['missing_prerequisite']} required by {prereq['dependent']}",
                "importance": 0.85,
                "confidence": 0.90, # We are highly confident it's missing if it's explicitly marked as stub
                "source_context": {"type": "kg_missing_prerequisite", "data": prereq}
            })
            
        # 2. Graph-based contradiction detection
        contradictions = await self.kg_reasoner.detect_contradictions(domain=domain)
        for contra in contradictions:
            gaps.append({
                "domain": domain or "general",
                "description": f"Contradiction detected between {contra['concept_a']} and {contra['concept_b']}: {contra['reason']}",
                "importance": 0.95,
                "confidence": 0.80, # Confidence that this needs resolution
                "source_context": {"type": "kg_contradiction", "data": contra}
            })
            
        # 3. Weak Domain detection
        if domain:
            coverage = await self.kg_reasoner.get_domain_coverage(domain)
            if coverage["concept_count"] > 0 and coverage["density"] < 1.0:
                gaps.append({
                    "domain": domain,
                    "description": f"Low concept density in domain {domain}. Only {coverage['density']:.2f} connections per concept.",
                    "importance": 0.70,
                    "confidence": 0.95,
                    "source_context": {"type": "kg_weak_domain", "data": coverage}
                })
                
        # 4. Vector-store based low-confidence regions could be added here
        # E.g. finding clusters of memories that have negative sentiment or "failure" outcomes
        
        return gaps
