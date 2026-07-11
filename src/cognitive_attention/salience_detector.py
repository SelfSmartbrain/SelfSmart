"""
Salience Detector - Detects salient information

The SalienceDetector is responsible for:
- Detecting important/salient information
- Calculating novelty and surprise
- Identifying patterns and anomalies
- Filtering noise from signal
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib


logger = logging.getLogger(__name__)


class SalienceType(Enum):
    """Types of salience"""
    NOVELTY = "novelty"  # New information
    URGENCY = "urgency"  # Time-sensitive
    IMPORTANCE = "importance"  # Goal-relevant
    ANOMALY = "anomaly"  # Unexpected/unusual
    COMPLEXITY = "complexity"  # Complex/interesting


@dataclass
class SalienceSignal:
    """A salience signal"""
    salience_type: SalienceType
    strength: float  # 0.0 to 1.0
    source: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SalienceProfile:
    """Salience profile for information"""
    overall_salience: float
    signals: List[SalienceSignal]
    confidence: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class SalienceDetector:
    """
    Detects salient information from input.
    
    Similar to biological attention systems, this detector identifies
    what information deserves cognitive resources based on:
    - Novelty (is this new?)
    - Urgency (is this time-sensitive?)
    - Importance (is this goal-relevant?)
    - Anomaly (is this unusual?)
    - Complexity (is this interesting?)
    """
    
    def __init__(
        self,
        novelty_threshold: float = 0.3,
        anomaly_threshold: float = 0.7,
        history_window: int = 100,
    ):
        self.novelty_threshold = novelty_threshold
        self.anomaly_threshold = anomaly_threshold
        self.history_window = history_window
        
        # History for novelty detection
        self._content_history: List[Tuple[str, float]] = []
        self._pattern_history: Dict[str, int] = defaultdict(int)
        
        # Baseline for anomaly detection
        self._baselines: Dict[str, List[float]] = defaultdict(list)
        
        # Statistics
        self._detections_made = 0
        self._novel_detections = 0
        self._anomaly_detections = 0
    
    async def initialize(self) -> None:
        """Initialize the salience detector"""
        logger.info("SalienceDetector initialized")
    
    async def detect(
        self,
        information: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> SalienceProfile:
        """
        Detect salience in information.
        
        Args:
            information: Information to analyze
            context: Additional context
            
        Returns:
            Salience profile
        """
        signals = []
        
        # Detect novelty
        novelty_signal = await self._detect_novelty(information)
        if novelty_signal.strength > self.novelty_threshold:
            signals.append(novelty_signal)
        
        # Detect urgency
        urgency_signal = await self._detect_urgency(information)
        if urgency_signal.strength > 0.3:
            signals.append(urgency_signal)
        
        # Detect importance
        importance_signal = await self._detect_importance(information, context)
        if importance_signal.strength > 0.3:
            signals.append(importance_signal)
        
        # Detect anomaly
        anomaly_signal = await self._detect_anomaly(information)
        if anomaly_signal.strength > self.anomaly_threshold:
            signals.append(anomaly_signal)
        
        # Detect complexity
        complexity_signal = await self._detect_complexity(information)
        if complexity_signal.strength > 0.5:
            signals.append(complexity_signal)
        
        # Calculate overall salience
        overall_salience = self._calculate_overall_salience(signals)
        
        # Calculate confidence
        confidence = min(1.0, len(signals) / 3.0)
        
        # Update history
        await self._update_history(information)
        
        self._detections_made += 1
        
        profile = SalienceProfile(
            overall_salience=overall_salience,
            signals=signals,
            confidence=confidence,
        )
        
        logger.debug(
            f"Detected salience: {overall_salience:.2f} "
            f"({len(signals)} signals, confidence: {confidence:.2f})"
        )
        
        return profile
    
    async def _detect_novelty(self, information: Dict[str, Any]) -> SalienceSignal:
        """Detect novelty in information"""
        content = str(information)
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Check if this content has been seen recently
        recent_hashes = [h for h, _ in self._content_history[-self.history_window:]]
        
        if content_hash in recent_hashes:
            novelty = 0.0
        else:
            # Calculate novelty based on similarity to recent content
            novelty = 1.0 - self._calculate_similarity(content, recent_hashes)
        
        if novelty > 0.5:
            self._novel_detections += 1
        
        return SalienceSignal(
            salience_type=SalienceType.NOVELTY,
            strength=novelty,
            source="novelty_detector",
            metadata={"content_hash": content_hash},
        )
    
    def _calculate_similarity(
        self,
        content: str,
        recent_hashes: List[str],
    ) -> float:
        """Calculate similarity to recent content"""
        if not recent_hashes:
            return 0.0
        
        # Simple similarity: check for common words
        content_words = set(content.lower().split())
        
        # In full implementation, would use semantic similarity
        # For now, use a simple heuristic
        return 0.3  # Placeholder
    
    async def _detect_urgency(self, information: Dict[str, Any]) -> SalienceSignal:
        """Detect urgency in information"""
        urgency = 0.0
        
        # Check for urgency keywords
        urgency_keywords = ["urgent", "immediate", "critical", "emergency", "asap"]
        content = str(information).lower()
        
        for keyword in urgency_keywords:
            if keyword in content:
                urgency += 0.2
        
        # Check for explicit urgency flag
        urgency = max(urgency, information.get("urgency", 0.0))
        
        # Check for deadline
        if "deadline" in information or "due" in content:
            urgency += 0.3
        
        return SalienceSignal(
            salience_type=SalienceType.URGENCY,
            strength=min(1.0, urgency),
            source="urgency_detector",
        )
    
    async def _detect_importance(
        self,
        information: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> SalienceSignal:
        """Detect importance based on goals and context"""
        importance = 0.0
        
        # Check for explicit importance
        importance = max(importance, information.get("importance", 0.0))
        
        # Check for priority
        priority = information.get("priority", 0.0)
        importance = max(importance, priority / 10.0)
        
        # Check goal alignment if context provided
        if context:
            goals = context.get("goals", [])
            content = str(information).lower()
            
            for goal in goals:
                if goal.lower() in content:
                    importance += 0.2
            
            if goals:
                importance = min(1.0, importance / len(goals))
        
        return SalienceSignal(
            salience_type=SalienceType.IMPORTANCE,
            strength=min(1.0, importance),
            source="importance_detector",
        )
    
    async def _detect_anomaly(self, information: Dict[str, Any]) -> SalienceSignal:
        """Detect anomalies in information"""
        anomaly_score = 0.0
        
        # Extract numeric values for anomaly detection
        numeric_values = self._extract_numeric_values(information)
        
        for key, value in numeric_values.items():
            # Update baseline
            self._baselines[key].append(value)
            if len(self._baselines[key]) > self.history_window:
                self._baselines[key].pop(0)
            
            # Check if value deviates from baseline
            if len(self._baselines[key]) > 10:
                baseline = self._baselines[key]
                mean = sum(baseline) / len(baseline)
                std = (sum((x - mean) ** 2 for x in baseline) / len(baseline)) ** 0.5
                
                if std > 0:
                    z_score = abs(value - mean) / std
                    if z_score > 2.0:  # 2 standard deviations
                        anomaly_score = max(anomaly_score, min(1.0, z_score / 3.0))
        
        if anomaly_score > self.anomaly_threshold:
            self._anomaly_detections += 1
        
        return SalienceSignal(
            salience_type=SalienceType.ANOMALY,
            strength=anomaly_score,
            source="anomaly_detector",
        )
    
    def _extract_numeric_values(self, information: Dict[str, Any]) -> Dict[str, float]:
        """Extract numeric values from information"""
        numeric = {}
        
        for key, value in information.items():
            if isinstance(value, (int, float)):
                numeric[key] = float(value)
        
        return numeric
    
    async def _detect_complexity(self, information: Dict[str, Any]) -> SalienceSignal:
        """Detect complexity in information"""
        content = str(information)
        
        # Length-based complexity
        length_factor = min(1.0, len(content) / 1000.0)
        
        # Structure-based complexity
        nesting = content.count("{") + content.count("[")
        nesting_factor = min(1.0, nesting / 20.0)
        
        # Diversity-based complexity (unique words)
        words = content.split()
        unique_words = len(set(words)) if words else 0
        diversity_factor = unique_words / len(words) if words else 0.0
        
        complexity = (length_factor + nesting_factor + diversity_factor) / 3.0
        
        return SalienceSignal(
            salience_type=SalienceType.COMPLEXITY,
            strength=complexity,
            source="complexity_detector",
        )
    
    def _calculate_overall_salience(self, signals: List[SalienceSignal]) -> float:
        """Calculate overall salience from signals"""
        if not signals:
            return 0.0
        
        # Weighted average of signal strengths
        weights = {
            SalienceType.NOVELTY: 0.3,
            SalienceType.URGENCY: 0.25,
            SalienceType.IMPORTANCE: 0.25,
            SalienceType.ANOMALY: 0.1,
            SalienceType.COMPLEXITY: 0.1,
        }
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for signal in signals:
            weight = weights.get(signal.salience_type, 0.2)
            weighted_sum += signal.strength * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_sum / total_weight
        
        return 0.0
    
    async def _update_history(self, information: Dict[str, Any]) -> None:
        """Update detection history"""
        content = str(information)
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        self._content_history.append((content_hash, datetime.now().timestamp()))
        
        # Keep only recent history
        if len(self._content_history) > self.history_window:
            self._content_history.pop(0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get detector metrics"""
        return {
            "detections_made": self._detections_made,
            "novel_detections": self._novel_detections,
            "anomaly_detections": self._anomaly_detections,
            "history_size": len(self._content_history),
            "baselines_tracked": len(self._baselines),
        }
