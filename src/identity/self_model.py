"""
Self Model - Model of own capabilities and limitations

The SelfModel is responsible for:
- Modeling own capabilities
- Tracking performance and limitations
- Self-assessment and calibration
- Learning from experience
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for self-assessment"""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 1.0


@dataclass
class CapabilityAssessment:
    """Assessment of a capability"""
    capability: str
    confidence: float
    performance_history: List[float] = field(default_factory=list)
    last_assessed: float = field(default_factory=lambda: datetime.now().timestamp())
    limitations: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)


@dataclass
class PerformanceRecord:
    """Record of performance on a task"""
    task_type: str
    success: bool
    confidence: float
    duration: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelfModel:
    """
    Model of own capabilities and limitations.
    
    Provides:
    - Capability assessment
    - Performance tracking
    - Self-calibration
    - Limitation awareness
    """
    
    def __init__(self):
        self._capabilities: Dict[str, CapabilityAssessment] = {}
        self._performance_history: List[PerformanceRecord] = []
        
        # Self-knowledge
        self._known_limitations: List[str] = []
        self._known_strengths: List[str] = []
        
        # Calibration
        self._confidence_calibration: Dict[str, float] = {}
        
        # Statistics
        self._assessments_made = 0
        self._performance_records = 0
    
    async def initialize(self) -> None:
        """Initialize the self model"""
        logger.info("SelfModel initialized")
    
    async def assess_capability(
        self,
        capability: str,
        confidence: float,
        limitations: Optional[List[str]] = None,
        strengths: Optional[List[str]] = None,
    ) -> CapabilityAssessment:
        """
        Assess a capability.
        
        Args:
            capability: Capability name
            confidence: Confidence level (0.0 to 1.0)
            limitations: Known limitations
            strengths: Known strengths
            
        Returns:
            Capability assessment
        """
        if capability in self._capabilities:
            # Update existing assessment
            assessment = self._capabilities[capability]
            assessment.confidence = confidence
            assessment.last_assessed = datetime.now().timestamp()
            
            if limitations:
                assessment.limitations = limitations
            if strengths:
                assessment.strengths = strengths
        else:
            # Create new assessment
            assessment = CapabilityAssessment(
                capability=capability,
                confidence=confidence,
                limitations=limitations or [],
                strengths=strengths or [],
            )
            self._capabilities[capability] = assessment
        
        self._assessments_made += 1
        
        logger.debug(f"Assessed capability {capability}: confidence={confidence:.2f}")
        return assessment
    
    async def record_performance(
        self,
        task_type: str,
        success: bool,
        confidence: float,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record performance on a task.
        
        Args:
            task_type: Type of task
            success: Whether task was successful
            confidence: Confidence in performance
            duration: Task duration
            metadata: Additional metadata
        """
        record = PerformanceRecord(
            task_type=task_type,
            success=success,
            confidence=confidence,
            duration=duration,
            metadata=metadata or {},
        )
        
        self._performance_history.append(record)
        self._performance_records += 1
        
        # Update capability assessment if exists
        if task_type in self._capabilities:
            assessment = self._capabilities[task_type]
            assessment.performance_history.append(confidence if success else 0.0)
            
            # Keep only recent history
            if len(assessment.performance_history) > 100:
                assessment.performance_history.pop(0)
        
        logger.debug(f"Recorded performance: {task_type} success={success}")
    
    def get_capability_assessment(
        self,
        capability: str,
    ) -> Optional[CapabilityAssessment]:
        """Get assessment for a capability"""
        return self._capabilities.get(capability)
    
    def get_average_performance(
        self,
        task_type: str,
        recent_only: bool = True,
        limit: int = 50,
    ) -> float:
        """
        Get average performance for a task type.
        
        Args:
            task_type: Task type
            recent_only: Use only recent records
            limit: Maximum number of records to consider
            
        Returns:
            Average performance score
        """
        records = [r for r in self._performance_history if r.task_type == task_type]
        
        if recent_only:
            records = records[-limit:]
        
        if not records:
            return 0.5  # Default
        
        return sum(r.confidence for r in records if r.success) / len(records)
    
    def get_success_rate(
        self,
        task_type: Optional[str] = None,
        recent_only: bool = True,
        limit: int = 50,
    ) -> float:
        """
        Get success rate for tasks.
        
        Args:
            task_type: Specific task type (optional)
            recent_only: Use only recent records
            limit: Maximum number of records
            
        Returns:
            Success rate (0.0 to 1.0)
        """
        records = self._performance_history
        
        if task_type:
            records = [r for r in records if r.task_type == task_type]
        
        if recent_only:
            records = records[-limit:]
        
        if not records:
            return 0.5  # Default
        
        return sum(1 for r in records if r.success) / len(records)
    
    async def calibrate_confidence(
        self,
        task_type: str,
        predicted_confidence: float,
        actual_outcome: bool,
    ) -> float:
        """
        Calibrate confidence predictions.
        
        Args:
            task_type: Task type
            predicted_confidence: Predicted confidence
            actual_outcome: Actual outcome
            
        Returns:
            Calibration adjustment
        """
        # Calculate error
        if actual_outcome:
            error = 1.0 - predicted_confidence
        else:
            error = predicted_confidence
        
        # Update calibration
        if task_type not in self._confidence_calibration:
            self._confidence_calibration[task_type] = 0.0
        
        # Simple moving average
        current = self._confidence_calibration[task_type]
        adjustment = (current * 0.9) + (error * 0.1)
        self._confidence_calibration[task_type] = adjustment
        
        logger.debug(f"Calibrated confidence for {task_type}: {adjustment:.3f}")
        return adjustment
    
    def get_calibration(self, task_type: str) -> float:
        """Get calibration value for a task type"""
        return self._confidence_calibration.get(task_type, 0.0)
    
    async def identify_limitations(self) -> List[str]:
        """
        Identify current limitations based on performance.
        
        Returns:
            List of identified limitations
        """
        limitations = []
        
        # Analyze performance history
        for capability, assessment in self._capabilities.items():
            if assessment.confidence < 0.5:
                limitations.append(f"Low confidence in {capability}")
            
            if assessment.performance_history:
                avg_performance = sum(assessment.performance_history) / len(assessment.performance_history)
                if avg_performance < 0.6:
                    limitations.append(f"Poor performance in {capability}")
        
        # Add known limitations
        limitations.extend(self._known_limitations)
        
        return list(set(limitations))
    
    async def identify_strengths(self) -> List[str]:
        """
        Identify current strengths based on performance.
        
        Returns:
            List of identified strengths
        """
        strengths = []
        
        # Analyze performance history
        for capability, assessment in self._capabilities.items():
            if assessment.confidence > 0.7:
                strengths.append(f"High confidence in {capability}")
            
            if assessment.performance_history:
                avg_performance = sum(assessment.performance_history) / len(assessment.performance_history)
                if avg_performance > 0.8:
                    strengths.append(f"Strong performance in {capability}")
        
        # Add known strengths
        strengths.extend(self._known_strengths)
        
        return list(set(strengths))
    
    def can_handle_task(
        self,
        task_type: str,
        min_confidence: float = 0.5,
    ) -> bool:
        """
        Determine if can handle a task.
        
        Args:
            task_type: Task type
            min_confidence: Minimum required confidence
            
        Returns:
            True if can handle
        """
        assessment = self._capabilities.get(task_type)
        
        if assessment is None:
            return False
        
        return assessment.confidence >= min_confidence
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get self model metrics"""
        return {
            "assessments_made": self._assessments_made,
            "performance_records": self._performance_records,
            "capabilities_tracked": len(self._capabilities),
            "known_limitations": len(self._known_limitations),
            "known_strengths": len(self._known_strengths),
            "calibrated_tasks": len(self._confidence_calibration),
        }
