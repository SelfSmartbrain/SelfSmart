"""outcome_tracker.py

Phase 16H: Outcome Tracker

Tracks long-term outcomes of decisions.
Monitors:
- Decision outcomes over time
- Delayed effects
- Cumulative impact
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class OutcomeStatus(str, Enum):
    """Status of outcome tracking."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    MEASURED = "measured"
    VALIDATED = "validated"
    FAILED = "failed"


@dataclass
class OutcomeMeasurement:
    """A measurement of decision outcome."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    unit: str = ""
    measured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    time_since_decision: timedelta = field(default_factory=lambda: timedelta(0))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "unit": self.unit,
            "measured_at": self.measured_at.isoformat(),
            "time_since_decision_hours": self.time_since_decision.total_seconds() / 3600,
            "metadata": self.metadata,
        }


@dataclass
class OutcomeTracking:
    """Long-term tracking of a decision's outcomes."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    decision_made_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expected_outcomes: List[str] = field(default_factory=list)
    measurements: List[OutcomeMeasurement] = field(default_factory=list)
    status: OutcomeStatus = OutcomeStatus.PENDING
    final_assessment: Optional[str] = None
    cumulative_impact: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "decision_made_at": self.decision_made_at.isoformat(),
            "expected_outcomes": self.expected_outcomes,
            "measurements": [m.to_dict() for m in self.measurements],
            "status": self.status.value,
            "final_assessment": self.final_assessment,
            "cumulative_impact": self.cumulative_impact,
            "metadata": self.metadata,
        }


class OutcomeTracker:
    """Tracks long-term outcomes of decisions."""
    
    def __init__(self):
        self.trackings: Dict[str, OutcomeTracking] = {}
        self.trackings_by_decision: Dict[str, str] = {}  # decision_id -> tracking_id
        logger.info("OutcomeTracker initialized")
    
    def start_tracking(
        self,
        decision_id: str,
        decision_made_at: Optional[datetime] = None,
        expected_outcomes: Optional[List[str]] = None,
    ) -> OutcomeTracking:
        """Start tracking outcomes for a decision."""
        tracking = OutcomeTracking(
            decision_id=decision_id,
            decision_made_at=decision_made_at or datetime.now(timezone.utc),
            expected_outcomes=expected_outcomes or [],
        )
        
        self.trackings[tracking.id] = tracking
        self.trackings_by_decision[decision_id] = tracking.id
        
        logger.info(f"Started outcome tracking for decision {decision_id}")
        
        return tracking
    
    def add_measurement(
        self,
        decision_id: str,
        metric_name: str,
        metric_value: float,
        unit: str = "",
    ) -> OutcomeMeasurement:
        """Add a measurement to decision tracking."""
        tracking_id = self.trackings_by_decision.get(decision_id)
        if tracking_id is None:
            logger.warning(f"No tracking found for decision {decision_id}")
            # Auto-create tracking
            tracking = self.start_tracking(decision_id)
            tracking_id = tracking.id
        
        tracking = self.trackings[tracking_id]
        
        time_since = datetime.now(timezone.utc) - tracking.decision_made_at
        
        measurement = OutcomeMeasurement(
            decision_id=decision_id,
            metric_name=metric_name,
            metric_value=metric_value,
            unit=unit,
            time_since_decision=time_since,
        )
        
        tracking.measurements.append(measurement)
        tracking.status = OutcomeStatus.IN_PROGRESS
        
        logger.info(f"Added measurement {metric_name}={metric_value} for decision {decision_id}")
        
        return measurement
    
    def get_tracking(self, decision_id: str) -> Optional[OutcomeTracking]:
        """Get outcome tracking for a decision."""
        tracking_id = self.trackings_by_decision.get(decision_id)
        if tracking_id:
            return self.trackings.get(tracking_id)
        return None
    
    def get_measurements(
        self,
        decision_id: str,
        metric_name: Optional[str] = None,
    ) -> List[OutcomeMeasurement]:
        """Get measurements for a decision."""
        tracking = self.get_tracking(decision_id)
        if not tracking:
            return []
        
        if metric_name:
            return [m for m in tracking.measurements if m.metric_name == metric_name]
        
        return tracking.measurements
    
    def get_outcome_trend(
        self,
        decision_id: str,
        metric_name: str,
    ) -> Dict[str, Any]:
        """Get the trend of a specific metric over time."""
        measurements = self.get_measurements(decision_id, metric_name)
        
        if len(measurements) < 2:
            return {"error": "Not enough measurements to determine trend"}
        
        # Sort by time
        measurements.sort(key=lambda m: m.measured_at)
        
        values = [m.metric_value for m in measurements]
        
        # Calculate trend
        first_value = values[0]
        last_value = values[-1]
        
        if last_value > first_value:
            trend = "increasing"
        elif last_value < first_value:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Calculate rate of change
        time_diff = (measurements[-1].measured_at - measurements[0].measured_at).total_seconds()
        value_diff = last_value - first_value
        
        if time_diff > 0:
            rate = value_diff / time_diff  # per second
        else:
            rate = 0.0
        
        return {
            "decision_id": decision_id,
            "metric_name": metric_name,
            "trend": trend,
            "first_value": first_value,
            "last_value": last_value,
            "change": value_diff,
            "rate_per_second": rate,
            "measurement_count": len(measurements),
        }
    
    def finalize_tracking(
        self,
        decision_id: str,
        final_assessment: str,
        cumulative_impact: float,
    ) -> bool:
        """Finalize outcome tracking for a decision."""
        tracking = self.get_tracking(decision_id)
        if not tracking:
            return False
        
        tracking.status = OutcomeStatus.VALIDATED
        tracking.final_assessment = final_assessment
        tracking.cumulative_impact = cumulative_impact
        
        logger.info(f"Finalized tracking for decision {decision_id}")
        
        return True
    
    def get_trackings_by_status(self, status: OutcomeStatus) -> List[OutcomeTracking]:
        """Get all trackings with a specific status."""
        return [t for t in self.trackings.values() if t.status == status]
    
    def get_long_term_trackings(self, days: int = 30) -> List[OutcomeTracking]:
        """Get trackings for decisions made more than X days ago."""
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        
        return [
            t for t in self.trackings.values()
            if t.decision_made_at < threshold
        ]
    
    def get_tracking_statistics(self) -> Dict[str, Any]:
        """Get statistics about outcome tracking."""
        total_trackings = len(self.trackings)
        
        by_status = {
            status.value: len(self.get_trackings_by_status(status))
            for status in OutcomeStatus
        }
        
        total_measurements = sum(len(t.measurements) for t in self.trackings.values())
        
        return {
            "total_trackings": total_trackings,
            "by_status": by_status,
            "total_measurements": total_measurements,
            "avg_measurements_per_tracking": total_measurements / total_trackings if total_trackings > 0 else 0,
        }
