"""experiment_orchestrator.py

Orchestrates experiment design, execution, and analysis
within the scientific discovery loop.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ExperimentStatus(str, Enum):
    """Status of an experiment."""
    DESIGNED = "designed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Experiment:
    """An experiment in the discovery process."""
    experiment_id: str
    hypothesis: str
    design: Dict[str, Any]
    status: ExperimentStatus = ExperimentStatus.DESIGNED
    results: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "status": self.status.value,
            "has_results": self.results is not None,
            "created_at": self.created_at.isoformat(),
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.started_at and self.completed_at
                else None
            ),
        }


class ExperimentOrchestrator:
    """Orchestrates experiment lifecycle within the discovery loop."""
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self.experiment_queue: List[str] = []
        self.running_experiments: Dict[str, Experiment] = {}
        logger.info("ExperimentOrchestrator initialized")
    
    def design_experiment(
        self,
        hypothesis: str,
        variables: List[str],
        method: str = "controlled",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Experiment:
        """Design a new experiment."""
        experiment = Experiment(
            experiment_id=str(uuid.uuid4()),
            hypothesis=hypothesis,
            design={
                "variables": variables,
                "method": method,
                "parameters": parameters or {},
            },
        )
        
        self.experiments[experiment.experiment_id] = experiment
        self.experiment_queue.append(experiment.experiment_id)
        
        logger.info(f"Designed experiment {experiment.experiment_id} for hypothesis: {hypothesis[:50]}...")
        return experiment
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment."""
        if experiment_id not in self.experiments:
            return False
        
        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now(timezone.utc)
        
        self.running_experiments[experiment_id] = experiment
        
        logger.info(f"Started experiment {experiment_id}")
        return True
    
    def complete_experiment(
        self,
        experiment_id: str,
        results: Dict[str, Any],
    ) -> bool:
        """Complete an experiment with results."""
        if experiment_id not in self.experiments:
            return False
        
        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.COMPLETED
        experiment.results = results
        experiment.completed_at = datetime.now(timezone.utc)
        
        if experiment_id in self.running_experiments:
            del self.running_experiments[experiment_id]
        
        logger.info(f"Completed experiment {experiment_id}")
        return True
    
    def fail_experiment(
        self,
        experiment_id: str,
        error: str,
    ) -> bool:
        """Mark an experiment as failed."""
        if experiment_id not in self.experiments:
            return False
        
        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.FAILED
        experiment.results = {"error": error}
        experiment.completed_at = datetime.now(timezone.utc)
        
        if experiment_id in self.running_experiments:
            del self.running_experiments[experiment_id]
        
        logger.warning(f"Experiment {experiment_id} failed: {error}")
        return True
    
    def cancel_experiment(self, experiment_id: str) -> bool:
        """Cancel an experiment."""
        if experiment_id not in self.experiments:
            return False
        
        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.CANCELLED
        experiment.completed_at = datetime.now(timezone.utc)
        
        if experiment_id in self.running_experiments:
            del self.running_experiments[experiment_id]
        
        if experiment_id in self.experiment_queue:
            self.experiment_queue.remove(experiment_id)
        
        logger.info(f"Cancelled experiment {experiment_id}")
        return True
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get an experiment by ID."""
        return self.experiments.get(experiment_id)
    
    def get_queued_experiments(self) -> List[Experiment]:
        """Get all queued experiments."""
        return [
            self.experiments[eid]
            for eid in self.experiment_queue
            if eid in self.experiments
        ]
    
    def get_running_experiments(self) -> List[Experiment]:
        """Get all running experiments."""
        return list(self.running_experiments.values())
    
    def get_completed_experiments(self) -> List[Experiment]:
        """Get all completed experiments."""
        return [
            exp for exp in self.experiments.values()
            if exp.status == ExperimentStatus.COMPLETED
        ]
    
    def get_experiments_by_hypothesis(self, hypothesis: str) -> List[Experiment]:
        """Get experiments for a specific hypothesis."""
        return [
            exp for exp in self.experiments.values()
            if exp.hypothesis == hypothesis
        ]
    
    def analyze_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Analyze experiment results."""
        experiment = self.experiments.get(experiment_id)
        if not experiment or not experiment.results:
            return None
        
        # Simple analysis
        analysis = {
            "experiment_id": experiment_id,
            "hypothesis": experiment.hypothesis,
            "status": experiment.status.value,
            "results_summary": {
                "has_data": bool(experiment.results),
                "data_keys": list(experiment.results.keys()) if experiment.results else [],
            },
            "duration": (
                (experiment.completed_at - experiment.started_at).total_seconds()
                if experiment.started_at and experiment.completed_at
                else None
            ),
        }
        
        return analysis
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get experiment statistics."""
        status_counts = {}
        for experiment in self.experiments.values():
            status_counts[experiment.status.value] = status_counts.get(experiment.status.value, 0) + 1
        
        completed = self.get_completed_experiments()
        avg_duration = 0.0
        if completed:
            durations = [
                (exp.completed_at - exp.started_at).total_seconds()
                for exp in completed
                if exp.started_at and exp.completed_at
            ]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            "total_experiments": len(self.experiments),
            "by_status": status_counts,
            "queued": len(self.experiment_queue),
            "running": len(self.running_experiments),
            "completed": len(completed),
            "average_duration_seconds": avg_duration,
        }
