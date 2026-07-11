from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class CausalLink(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_event_id: uuid.UUID
    target_event_id: uuid.UUID
    relation_type: str  # CAUSES, ENABLES, PREVENTS, INHIBITS, DEPENDS_ON, CORRELATES_WITH
    strength: float = Field(ge=0.0, le=1.0)
    evidence: str
    is_spurious: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CausalEvaluationResult(BaseModel):
    model_config = {"from_attributes": True}

    links: List[CausalLink]
    detected_spurious_correlations: List[uuid.UUID]
    confidence_score: float


class CausalReasoner:
    """
    Infers causal links and evaluates their strength based on recent events
    and execution logs, identifying true causality versus spurious correlations.
    """

    def __init__(self, llm_client: Any) -> None:
        self.llm_client = llm_client

    async def infer_causal_links(
        self, recent_events: List[Dict[str, Any]], execution_logs: List[Dict[str, Any]]
    ) -> CausalEvaluationResult:
        logger.info(f"Inferring causal links for {len(recent_events)} events and {len(execution_logs)} logs.")
        try:
            links: List[CausalLink] = []
            spurious_ids: List[uuid.UUID] = []

            # Analyze temporal sequences to identify potential causal relationships
            for i, event1 in enumerate(recent_events):
                for event2 in recent_events[i+1:]:
                    # Check temporal precedence
                    if self._is_temporally_preceding(event1, event2):
                        # Analyze execution logs for correlation
                        correlation_strength = self._compute_correlation(
                            event1, event2, execution_logs
                        )
                        
                        if correlation_strength > 0.5:
                            # Use LLM to validate causal relationship
                            causal_analysis = await self._llm_causal_validation(
                                event1, event2, execution_logs
                            )
                            
                            if causal_analysis["is_causal"]:
                                link = CausalLink(
                                    source_event_id=uuid.UUID(event1.get("id", str(uuid.uuid4()))),
                                    target_event_id=uuid.UUID(event2.get("id", str(uuid.uuid4()))),
                                    relation_type=causal_analysis["relation_type"],
                                    strength=causal_analysis["strength"],
                                    evidence=causal_analysis["evidence"],
                                    is_spurious=False
                                )
                                links.append(link)
                            elif causal_analysis["is_spurious"]:
                                spurious_ids.append(uuid.UUID(event1.get("id", str(uuid.uuid4()))))

            result = CausalEvaluationResult(
                links=links,
                detected_spurious_correlations=spurious_ids,
                confidence_score=self._compute_overall_confidence(links),
            )
            return result
        except Exception as e:
            logger.error(f"Error inferring causal links: {e}")
            raise

    async def evaluate_causal_strength(self, link: CausalLink, new_evidence: Dict[str, Any]) -> CausalLink:
        logger.info(f"Evaluating causal strength for link {link.id}")
        try:
            # Analyze new evidence to update causal strength
            evidence_support = self._analyze_evidence_support(link, new_evidence)
            
            # Bayesian update of strength
            prior_strength = link.strength
            likelihood_ratio = evidence_support / (1.0 - evidence_support + 0.001)
            posterior_strength = (prior_strength * likelihood_ratio) / (
                prior_strength * likelihood_ratio + (1 - prior_strength)
            )
            
            # Smooth update to avoid extreme jumps
            updated_strength = 0.7 * prior_strength + 0.3 * posterior_strength
            link.strength = min(1.0, max(0.0, updated_strength))
            
            # Update evidence string
            link.evidence = f"{link.evidence} | New evidence: {new_evidence}"
            
            return link
        except Exception as e:
            logger.error(f"Error evaluating causal strength: {e}")
            raise

    async def detect_spurious_correlations(
        self, links: List[CausalLink], logs: List[Dict[str, Any]]
    ) -> List[CausalLink]:
        logger.info("Detecting spurious correlations among causal links...")
        try:
            spurious_links = []
            for link in links:
                # Check for confounding variables
                has_confounder = await self._check_confounders(link, logs)
                
                # Check for temporal coincidence vs causal sequence
                temporal_score = self._compute_temporal_score(link, logs)
                
                # Check for statistical significance
                statistical_significance = self._compute_statistical_significance(link, logs)
                
                # Determine if spurious based on multiple criteria
                is_spurious = (
                    has_confounder or
                    temporal_score < 0.3 or
                    statistical_significance < 0.05 or
                    (link.strength < 0.3 and link.relation_type == "CORRELATES_WITH")
                )
                
                if is_spurious:
                    link.is_spurious = True
                    spurious_links.append(link)
                    logger.debug(f"Marked link {link.id} as spurious")
                    
            return spurious_links
        except Exception as e:
            logger.error(f"Error detecting spurious correlations: {e}")
            raise

    def _is_temporally_preceding(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> bool:
        """Check if event1 temporally precedes event2."""
        time1 = event1.get("timestamp")
        time2 = event2.get("timestamp")
        if time1 and time2:
            return time1 < time2
        return False

    def _compute_correlation(
        self, event1: Dict[str, Any], event2: Dict[str, Any], logs: List[Dict[str, Any]]
    ) -> float:
        """Compute correlation strength between two events based on execution logs."""
        # Simplified correlation based on co-occurrence in logs
        event1_id = event1.get("id")
        event2_id = event2.get("id")
        
        co_occurrences = 0
        total_logs = len(logs)
        
        for log in logs:
            log_events = log.get("events", [])
            event_ids = [e.get("id") for e in log_events]
            if event1_id in event_ids and event2_id in event_ids:
                co_occurrences += 1
        
        if total_logs == 0:
            return 0.0
        
        return co_occurrences / total_logs

    async def _llm_causal_validation(
        self, event1: Dict[str, Any], event2: Dict[str, Any], logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use LLM to validate causal relationship between events."""
        # In production, this would call an LLM to analyze the relationship
        # For now, return a simplified analysis
        correlation = self._compute_correlation(event1, event2, logs)
        
        if correlation > 0.7:
            return {
                "is_causal": True,
                "is_spurious": False,
                "relation_type": "CAUSES",
                "strength": min(0.9, correlation + 0.1),
                "evidence": f"High correlation ({correlation:.2f}) in execution logs"
            }
        elif correlation > 0.4:
            return {
                "is_causal": True,
                "is_spurious": False,
                "relation_type": "ENABLES",
                "strength": correlation,
                "evidence": f"Moderate correlation ({correlation:.2f}) in execution logs"
            }
        else:
            return {
                "is_causal": False,
                "is_spurious": True,
                "relation_type": "CORRELATES_WITH",
                "strength": correlation,
                "evidence": f"Low correlation ({correlation:.2f}) suggests spurious relationship"
            }

    def _compute_overall_confidence(self, links: List[CausalLink]) -> float:
        """Compute overall confidence score for the causal evaluation."""
        if not links:
            return 0.0
        
        avg_strength = sum(link.strength for link in links) / len(links)
        non_spurious_ratio = sum(1 for link in links if not link.is_spurious) / len(links)
        
        return avg_strength * non_spurious_ratio

    def _analyze_evidence_support(self, link: CausalLink, new_evidence: Dict[str, Any]) -> float:
        """Analyze how much new evidence supports the causal link."""
        # Simplified analysis based on evidence type
        evidence_type = new_evidence.get("type", "unknown")
        
        if evidence_type == "direct_observation":
            return 0.9
        elif evidence_type == "statistical":
            return 0.7
        elif evidence_type == "anecdotal":
            return 0.4
        else:
            return 0.5

    async def _check_confounders(self, link: CausalLink, logs: List[Dict[str, Any]]) -> bool:
        """Check for confounding variables that might explain the correlation."""
        # Simplified check: look for common causes in logs
        source_id = str(link.source_event_id)
        target_id = str(link.target_event_id)
        
        for log in logs:
            events = log.get("events", [])
            event_ids = [e.get("id") for e in events]
            
            # If both events appear with a third event frequently, it might be a confounder
            if source_id in event_ids and target_id in event_ids:
                if len(event_ids) > 2:
                    return True
        
        return False

    def _compute_temporal_score(self, link: CausalLink, logs: List[Dict[str, Any]]) -> float:
        """Compute temporal consistency score for the causal link."""
        # Simplified temporal analysis
        source_id = str(link.source_event_id)
        target_id = str(link.target_event_id)
        
        correct_order_count = 0
        total_occurrences = 0
        
        for log in logs:
            events = log.get("events", [])
            source_index = None
            target_index = None
            
            for i, event in enumerate(events):
                if event.get("id") == source_id:
                    source_index = i
                elif event.get("id") == target_id:
                    target_index = i
            
            if source_index is not None and target_index is not None:
                total_occurrences += 1
                if source_index < target_index:
                    correct_order_count += 1
        
        if total_occurrences == 0:
            return 0.0
        
        return correct_order_count / total_occurrences

    def _compute_statistical_significance(self, link: CausalLink, logs: List[Dict[str, Any]]) -> float:
        """Compute statistical significance of the causal relationship."""
        # Simplified significance based on occurrence frequency
        source_id = str(link.source_event_id)
        target_id = str(link.target_event_id)
        
        source_occurrences = sum(1 for log in logs if any(e.get("id") == source_id for e in log.get("events", [])))
        joint_occurrences = sum(
            1 for log in logs 
            if source_id in [e.get("id") for e in log.get("events", [])] and
            target_id in [e.get("id") for e in log.get("events", [])]
        )
        
        if source_occurrences == 0:
            return 0.0
        
        # Simplified p-value approximation
        conditional_probability = joint_occurrences / source_occurrences
        return 1.0 - conditional_probability
