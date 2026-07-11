"""success_pattern_detector.py

Phase 16C: Success Pattern Detector

Identifies patterns that consistently lead to successful outcomes.
Focuses on:
- High-success decision patterns
- Contextual success factors
- Strategy success patterns
- Resource allocation patterns that work
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class SuccessFactorType(str, Enum):
    """Types of success factors."""
    CONTEXT = "context"
    STRATEGY = "strategy"
    RESOURCE = "resource"
    TIMING = "timing"
    AGENT = "agent"


@dataclass
class SuccessPattern:
    """A pattern associated with successful outcomes."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    factor_type: SuccessFactorType = SuccessFactorType.CONTEXT
    success_rate: float = 0.0
    sample_size: int = 0
    confidence: float = 0.0
    conditions: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "factor_type": self.factor_type.value,
            "success_rate": self.success_rate,
            "sample_size": self.sample_size,
            "confidence": self.confidence,
            "conditions": self.conditions,
            "recommendations": self.recommendations,
            "examples": self.examples[:5],
            "metadata": self.metadata,
        }


class SuccessPatternDetector:
    """Detects patterns that lead to successful outcomes."""
    
    def __init__(self):
        self.success_patterns: Dict[str, SuccessPattern] = {}
        self.decision_history: List[Dict[str, Any]] = []
        logger.info("SuccessPatternDetector initialized")
    
    def add_decision(self, decision_data: Dict[str, Any]) -> None:
        """Add a decision to the history."""
        self.decision_history.append(decision_data)
        
        # Re-detect patterns periodically
        if len(self.decision_history) % 10 == 0:
            self.detect_patterns()
    
    def detect_patterns(self) -> List[SuccessPattern]:
        """Detect success patterns from decision history."""
        if len(self.decision_history) < 5:
            logger.info("Not enough decisions to detect success patterns")
            return []
        
        # Separate successful from failed decisions
        successful = [
            d for d in self.decision_history
            if d.get("outcome", {}).get("success", False)
        ]
        
        failed = [
            d for d in self.decision_history
            if d.get("outcome") and not d.get("outcome", {}).get("success", False)
        ]
        
        if len(successful) < 3:
            logger.info("Not enough successful decisions to detect patterns")
            return []
        
        patterns = []
        
        # Detect context patterns
        patterns.extend(self._detect_context_patterns(successful, failed))
        
        # Detect strategy patterns
        patterns.extend(self._detect_strategy_patterns(successful, failed))
        
        # Detect resource patterns
        patterns.extend(self._detect_resource_patterns(successful, failed))
        
        # Detect timing patterns
        patterns.extend(self._detect_timing_patterns(successful, failed))
        
        # Store patterns
        for pattern in patterns:
            self.success_patterns[pattern.id] = pattern
        
        logger.info(f"Detected {len(patterns)} success patterns")
        
        return patterns
    
    def _detect_context_patterns(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
    ) -> List[SuccessPattern]:
        """Detect context patterns that lead to success."""
        patterns = []
        
        # Analyze time horizon patterns
        success_horizons = [d.get("context", {}).get("time_horizon") for d in successful]
        fail_horizons = [d.get("context", {}).get("time_horizon") for d in failed]
        
        from collections import Counter
        success_horizon_counts = Counter([h for h in success_horizons if h])
        fail_horizon_counts = Counter([h for h in fail_horizons if h])
        
        for horizon, count in success_horizon_counts.most_common():
            if count >= 3:
                success_rate = count / len(successful)
                fail_count = fail_horizon_counts.get(horizon, 0)
                fail_rate = fail_count / len(failed) if failed else 0
                
                # Only include if success rate is significantly higher
                if success_rate > fail_rate + 0.2:
                    pattern = SuccessPattern(
                        name=f"Time Horizon: {horizon}",
                        description=f"Decisions with {horizon} time horizon have higher success rate",
                        factor_type=SuccessFactorType.CONTEXT,
                        success_rate=success_rate,
                        sample_size=count,
                        confidence=min(1.0, count / 10),
                        conditions={"time_horizon": horizon},
                        recommendations=[
                            f"Consider using {horizon} time horizon for similar decisions",
                        ],
                        examples=[d.get("id", "") for d in successful[:3]],
                    )
                    patterns.append(pattern)
        
        # Analyze risk tolerance patterns
        success_risks = [d.get("context", {}).get("risk_tolerance", 0.5) for d in successful]
        fail_risks = [d.get("context", {}).get("risk_tolerance", 0.5) for d in failed]
        
        # Bin risk tolerance
        def bin_risk(risk):
            if risk < 0.3:
                return "low"
            elif risk < 0.7:
                return "medium"
            else:
                return "high"
        
        success_risk_bins = [bin_risk(r) for r in success_risks]
        fail_risk_bins = [bin_risk(r) for r in fail_risks]
        
        success_risk_counts = Counter(success_risk_bins)
        fail_risk_counts = Counter(fail_risk_bins)
        
        for risk_bin, count in success_risk_counts.most_common():
            if count >= 3:
                success_rate = count / len(successful)
                fail_count = fail_risk_counts.get(risk_bin, 0)
                fail_rate = fail_count / len(failed) if failed else 0
                
                if success_rate > fail_rate + 0.2:
                    pattern = SuccessPattern(
                        name=f"Risk Tolerance: {risk_bin}",
                        description=f"Decisions with {risk_bin} risk tolerance have higher success rate",
                        factor_type=SuccessFactorType.CONTEXT,
                        success_rate=success_rate,
                        sample_size=count,
                        confidence=min(1.0, count / 10),
                        conditions={"risk_tolerance_bin": risk_bin},
                        recommendations=[
                            f"Consider using {risk_bin} risk tolerance for similar decisions",
                        ],
                        examples=[d.get("id", "") for d in successful[:3]],
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_strategy_patterns(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
    ) -> List[SuccessPattern]:
        """Detect strategy patterns that lead to success."""
        patterns = []
        
        # Analyze option selection patterns
        success_options = []
        for decision in successful:
            options = decision.get("options", [])
            selected_id = decision.get("selected_option_id")
            selected = next((opt for opt in options if opt.get("id") == selected_id), None)
            if selected:
                success_options.append(selected)
        
        # Look for common characteristics in successful options
        if len(success_options) >= 3:
            # Analyze utility score ranges
            utilities = [opt.get("utility_score", 0) for opt in success_options]
            avg_utility = sum(utilities) / len(utilities)
            
            high_utility_count = sum(1 for u in utilities if u > avg_utility)
            
            if high_utility_count >= len(success_options) * 0.7:
                pattern = SuccessPattern(
                    name="High Utility Selection",
                    description="Selecting options with above-average utility scores correlates with success",
                    factor_type=SuccessFactorType.STRATEGY,
                    success_rate=high_utility_count / len(success_options),
                    sample_size=len(success_options),
                    confidence=min(1.0, len(success_options) / 10),
                    conditions={"min_utility": avg_utility},
                    recommendations=[
                        "Prioritize options with higher utility scores",
                        f"Consider options with utility > {avg_utility:.2f}",
                    ],
                    examples=[opt.get("id", "") for opt in success_options[:3]],
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_resource_patterns(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
    ) -> List[SuccessPattern]:
        """Detect resource allocation patterns that lead to success."""
        patterns = []
        
        # Analyze resource availability in successful decisions
        success_resources = []
        for decision in successful:
            resources = decision.get("context", {}).get("available_resources", {})
            if resources:
                success_resources.append(resources)
        
        if len(success_resources) >= 3:
            # Look for common resource types
            from collections import Counter
            resource_types = []
            for resources in success_resources:
                resource_types.extend(resources.keys())
            
            resource_counts = Counter(resource_types)
            
            for resource_type, count in resource_counts.most_common(5):
                if count >= len(success_resources) * 0.5:
                    pattern = SuccessPattern(
                        name=f"Resource: {resource_type}",
                        description=f"Availability of {resource_type} resource correlates with success",
                        factor_type=SuccessFactorType.RESOURCE,
                        success_rate=count / len(success_resources),
                        sample_size=len(success_resources),
                        confidence=min(1.0, len(success_resources) / 10),
                        conditions={"resource_type": resource_type},
                        recommendations=[
                            f"Ensure {resource_type} resource is available before decision",
                        ],
                        examples=[d.get("id", "") for d in successful[:3]],
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_timing_patterns(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
    ) -> List[SuccessPattern]:
        """Detect timing patterns that lead to success."""
        patterns = []
        
        # Analyze decision timing
        from datetime import datetime
        
        success_hours = []
        for decision in successful:
            created_at = decision.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        success_hours.append(dt.hour)
                    except:
                        continue
                else:
                    success_hours.append(created_at.hour)
        
        if len(success_hours) >= 3:
            from collections import Counter
            hour_counts = Counter(success_hours)
            
            for hour, count in hour_counts.most_common(3):
                if count >= 3:
                    pattern = SuccessPattern(
                        name=f"Timing: Hour {hour}",
                        description=f"Decisions made around hour {hour} show higher success rate",
                        factor_type=SuccessFactorType.TIMING,
                        success_rate=count / len(success_hours),
                        sample_size=count,
                        confidence=min(1.0, count / 10),
                        conditions={"hour": hour},
                        recommendations=[
                            f"Consider timing decisions around hour {hour} when possible",
                        ],
                        examples=[d.get("id", "") for d in successful[:3]],
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def get_pattern(self, pattern_id: str) -> Optional[SuccessPattern]:
        """Get a success pattern by ID."""
        return self.success_patterns.get(pattern_id)
    
    def get_patterns_by_type(self, factor_type: SuccessFactorType) -> List[SuccessPattern]:
        """Get all patterns of a specific factor type."""
        return [p for p in self.success_patterns.values() if p.factor_type == factor_type]
    
    def get_high_confidence_patterns(self, threshold: float = 0.7) -> List[SuccessPattern]:
        """Get patterns with confidence above a threshold."""
        return [p for p in self.success_patterns.values() if p.confidence >= threshold]
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about success patterns."""
        total_patterns = len(self.success_patterns)
        
        by_type = {
            factor_type.value: len(self.get_patterns_by_type(factor_type))
            for factor_type in SuccessFactorType
        }
        
        avg_success_rate = (
            sum(p.success_rate for p in self.success_patterns.values()) / total_patterns
            if total_patterns > 0 else 0.0
        )
        
        return {
            "total_patterns": total_patterns,
            "by_type": by_type,
            "average_success_rate": avg_success_rate,
            "decisions_analyzed": len(self.decision_history),
        }
