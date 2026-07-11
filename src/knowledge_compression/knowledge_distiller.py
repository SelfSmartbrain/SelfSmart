"""knowledge_distiller.py

Distills large volumes of observations into essential insights.
Extracts the most valuable knowledge from raw data.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class InsightType(str, Enum):
    """Types of distilled insights."""
    PATTERN = "pattern"  # Recurring pattern
    ANOMALY = "anomaly"  # Unexpected deviation
    TREND = "trend"  # Directional change
    CORRELATION = "correlation"  # Relationship between variables
    CAUSAL = "causal"  # Cause-effect relationship
    BEST_PRACTICE = "best_practice"  # Optimal approach
    LESSON = "lesson"  # Learned lesson


@dataclass
class Insight:
    """A distilled insight from observations."""
    id: str
    type: InsightType
    description: str
    confidence: float
    evidence_count: int
    source_observations: List[str] = field(default_factory=list)
    actionable: bool = False
    impact: str = "medium"  # low, medium, high
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "actionable": self.actionable,
            "impact": self.impact,
            "created_at": self.created_at.isoformat(),
        }


class KnowledgeDistiller:
    """Distills essential insights from observations."""
    
    def __init__(self):
        self.insights: Dict[str, Insight] = {}
        self.distillation_history: List[Dict[str, Any]] = []
        logger.info("KnowledgeDistiller initialized")
    
    def distill(
        self,
        observations: List[str],
        max_insights: int = 20,
        min_confidence: float = 0.5,
    ) -> List[Insight]:
        """Distill insights from observations."""
        if not observations:
            return []
        
        insights = []
        
        # Extract patterns
        patterns = self._extract_patterns(observations)
        insights.extend(patterns)
        
        # Extract anomalies
        anomalies = self._extract_anomalies(observations)
        insights.extend(anomalies)
        
        # Extract trends
        trends = self._extract_trends(observations)
        insights.extend(trends)
        
        # Extract correlations
        correlations = self._extract_correlations(observations)
        insights.extend(correlations)
        
        # Extract best practices
        best_practices = self._extract_best_practices(observations)
        insights.extend(best_practices)
        
        # Extract lessons
        lessons = self._extract_lessons(observations)
        insights.extend(lessons)
        
        # Filter by confidence
        insights = [i for i in insights if i.confidence >= min_confidence]
        
        # Sort by confidence and impact
        insights.sort(key=lambda i: (i.confidence, i.evidence_count), reverse=True)
        
        # Limit to max_insights
        insights = insights[:max_insights]
        
        # Store insights
        for insight in insights:
            self.insights[insight.id] = insight
        
        # Record distillation
        self.distillation_history.append({
            "observation_count": len(observations),
            "insight_count": len(insights),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.info(f"Distilled {len(insights)} insights from {len(observations)} observations")
        return insights
    
    def _extract_patterns(self, observations: List[str]) -> List[Insight]:
        """Extract recurring patterns."""
        import uuid
        
        patterns = []
        
        # Find common n-grams
        n = 3
        ngram_counts = defaultdict(int)
        
        for obs in observations:
            words = obs.lower().split()
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i+n])
                ngram_counts[ngram] += 1
        
        # Get most common n-grams
        threshold = max(2, len(observations) * 0.1)
        for ngram, count in ngram_counts.items():
            if count >= threshold:
                confidence = min(1.0, count / len(observations))
                pattern = Insight(
                    id=str(uuid.uuid4()),
                    type=InsightType.PATTERN,
                    description=f"Recurring pattern: '{ngram}' appears {count} times",
                    confidence=confidence,
                    evidence_count=count,
                    source_observations=[obs for obs in observations if ngram in obs.lower()],
                    actionable=True,
                    impact="medium" if count > len(observations) * 0.2 else "low",
                )
                patterns.append(pattern)
        
        return patterns[:5]  # Limit to top 5 patterns
    
    def _extract_anomalies(self, observations: List[str]) -> List[Insight]:
        """Extract anomalies (outliers)."""
        import uuid
        
        anomalies = []
        
        # Find observations that are very different from others
        if len(observations) < 3:
            return anomalies
        
        # Calculate average length
        avg_length = sum(len(obs) for obs in observations) / len(observations)
        
        for obs in observations:
            length_diff = abs(len(obs) - avg_length)
            if length_diff > avg_length * 2:  # More than 2x different
                anomaly = Insight(
                    id=str(uuid.uuid4()),
                    type=InsightType.ANOMALY,
                    description=f"Anomaly: unusual observation (length {len(obs)} vs avg {avg_length:.0f})",
                    confidence=0.7,
                    evidence_count=1,
                    source_observations=[obs],
                    actionable=True,
                    impact="high",
                )
                anomalies.append(anomaly)
        
        return anomalies[:3]  # Limit to top 3 anomalies
    
    def _extract_trends(self, observations: List[str]) -> List[Insight]:
        """Extract trends from sequential observations."""
        import uuid
        import re
        
        trends = []
        
        # Extract numerical values
        numerical_values = []
        for obs in observations:
            nums = re.findall(r'\d+\.?\d*', obs)
            if nums:
                numerical_values.extend([float(n) for n in nums])
        
        if len(numerical_values) < 3:
            return trends
        
        # Check for increasing trend
        increases = sum(1 for i in range(1, len(numerical_values)) if numerical_values[i] > numerical_values[i-1])
        decreases = sum(1 for i in range(1, len(numerical_values)) if numerical_values[i] < numerical_values[i-1])
        
        if increases > decreases * 2:
            trend = Insight(
                id=str(uuid.uuid4()),
                type=InsightType.TREND,
                description="Trend: values generally increasing over time",
                confidence=increases / len(numerical_values),
                evidence_count=len(numerical_values),
                actionable=True,
                impact="medium",
            )
            trends.append(trend)
        elif decreases > increases * 2:
            trend = Insight(
                id=str(uuid.uuid4()),
                type=InsightType.TREND,
                description="Trend: values generally decreasing over time",
                confidence=decreases / len(numerical_values),
                evidence_count=len(numerical_values),
                actionable=True,
                impact="medium",
            )
            trends.append(trend)
        
        return trends
    
    def _extract_correlations(self, observations: List[str]) -> List[Insight]:
        """Extract correlations between terms."""
        import uuid
        
        correlations = []
        
        # Find terms that frequently co-occur
        term_cooccurrences = defaultdict(lambda: defaultdict(int))
        
        for obs in observations:
            words = list(set(obs.lower().split()))  # Unique words per observation
            for i, word1 in enumerate(words):
                for word2 in words[i+1:]:
                    term_cooccurrences[word1][word2] += 1
                    term_cooccurrences[word2][word1] += 1
        
        # Find strong correlations
        threshold = max(2, len(observations) * 0.15)
        for word1, related in term_cooccurrences.items():
            for word2, count in related.items():
                if count >= threshold:
                    correlation = Insight(
                        id=str(uuid.uuid4()),
                        type=InsightType.CORRELATION,
                        description=f"Correlation: '{word1}' and '{word2}' co-occur {count} times",
                        confidence=min(1.0, count / len(observations)),
                        evidence_count=count,
                        source_observations=[obs for obs in observations if word1 in obs.lower() and word2 in obs.lower()],
                        actionable=False,
                        impact="low",
                    )
                    correlations.append(correlation)
        
        # Deduplicate
        seen = set()
        unique_correlations = []
        for corr in correlations:
            key = tuple(sorted(corr.description.split(": ")[1].split("'")[1::2]))
            if key not in seen:
                seen.add(key)
                unique_correlations.append(corr)
        
        return unique_correlations[:5]
    
    def _extract_best_practices(self, observations: List[str]) -> List[Insight]:
        """Extract best practices from successful outcomes."""
        import uuid
        
        best_practices = []
        
        # Look for positive outcomes
        positive_keywords = ["success", "improved", "better", "optimal", "best", "effective"]
        
        for obs in observations:
            obs_lower = obs.lower()
            if any(keyword in obs_lower for keyword in positive_keywords):
                practice = Insight(
                    id=str(uuid.uuid4()),
                    type=InsightType.BEST_PRACTICE,
                    description=f"Best practice: {obs[:100]}...",
                    confidence=0.6,
                    evidence_count=1,
                    source_observations=[obs],
                    actionable=True,
                    impact="high",
                )
                best_practices.append(practice)
        
        return best_practices[:3]
    
    def _extract_lessons(self, observations: List[str]) -> List[Insight]:
        """Extract learned lessons."""
        import uuid
        
        lessons = []
        
        # Look for lesson indicators
        lesson_keywords = ["learned", "lesson", "realized", "discovered", "found", "concluded"]
        
        for obs in observations:
            obs_lower = obs.lower()
            if any(keyword in obs_lower for keyword in lesson_keywords):
                lesson = Insight(
                    id=str(uuid.uuid4()),
                    type=InsightType.LESSON,
                    description=f"Lesson: {obs[:100]}...",
                    confidence=0.7,
                    evidence_count=1,
                    source_observations=[obs],
                    actionable=True,
                    impact="medium",
                )
                lessons.append(lesson)
        
        return lessons[:3]
    
    def get_insight(self, insight_id: str) -> Optional[Insight]:
        """Get an insight by ID."""
        return self.insights.get(insight_id)
    
    def get_insights_by_type(self, insight_type: InsightType) -> List[Insight]:
        """Get all insights of a specific type."""
        return [i for i in self.insights.values() if i.type == insight_type]
    
    def get_actionable_insights(self) -> List[Insight]:
        """Get all actionable insights."""
        return [i for i in self.insights.values() if i.actionable]
    
    def get_high_impact_insights(self) -> List[Insight]:
        """Get all high-impact insights."""
        return [i for i in self.insights.values() if i.impact == "high"]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get distillation statistics."""
        type_counts = {}
        for insight in self.insights.values():
            type_counts[insight.type.value] = type_counts.get(insight.type.value, 0) + 1
        
        impact_counts = {}
        for insight in self.insights.values():
            impact_counts[insight.impact] = impact_counts.get(insight.impact, 0) + 1
        
        total_distillations = len(self.distillation_history)
        total_observations_processed = sum(d["observation_count"] for d in self.distillation_history)
        
        return {
            "total_insights": len(self.insights),
            "by_type": type_counts,
            "by_impact": impact_counts,
            "actionable_count": len(self.get_actionable_insights()),
            "total_distillations": total_distillations,
            "total_observations_processed": total_observations_processed,
            "average_insights_per_distillation": sum(d["insight_count"] for d in self.distillation_history) / total_distillations if total_distillations > 0 else 0.0,
        }
