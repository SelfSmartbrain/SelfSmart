"""Core validation framework for running experiments and collecting results."""

import time
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ValidationResult:
    """Result of a validation experiment."""
    
    experiment_id: str
    experiment_name: str
    status: ExperimentStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "error": self.error,
        }
    
    def save(self, output_dir: Path) -> None:
        """Save result to JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{self.experiment_id}.json"
        with open(output_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved validation result to {output_path}")


class ValidationFramework:
    """Framework for running validation experiments."""
    
    def __init__(self, output_dir: Path = Path("validation_results")):
        self.output_dir = output_dir
        self.results: List[ValidationResult] = []
        logger.info(f"Initialized ValidationFramework with output_dir={output_dir}")
    
    def run_experiment(
        self,
        experiment_name: str,
        experiment_func: Callable,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Run a single validation experiment."""
        experiment_id = f"{experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = ValidationResult(
            experiment_id=experiment_id,
            experiment_name=experiment_name,
            status=ExperimentStatus.PENDING,
            start_time=datetime.now(),
            metadata=metadata or {},
        )
        
        logger.info(f"Starting experiment: {experiment_name}")
        result.status = ExperimentStatus.RUNNING
        
        try:
            metrics = experiment_func()
            result.metrics = metrics
            result.status = ExperimentStatus.COMPLETED
            logger.info(f"Completed experiment: {experiment_name}")
        except Exception as e:
            result.status = ExperimentStatus.FAILED
            result.error = str(e)
            logger.error(f"Experiment failed: {experiment_name}", error=str(e))
        
        result.end_time = datetime.now()
        result.save(self.output_dir)
        self.results.append(result)
        
        return result
    
    def run_comparison(
        self,
        comparison_name: str,
        experiments: Dict[str, Callable],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, ValidationResult]:
        """Run multiple experiments for comparison."""
        logger.info(f"Running comparison: {comparison_name} with {len(experiments)} experiments")
        
        results = {}
        for exp_name, exp_func in experiments.items():
            full_name = f"{comparison_name}_{exp_name}"
            result = self.run_experiment(full_name, exp_func, metadata)
            results[exp_name] = result
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate summary report of all experiments."""
        report = {
            "total_experiments": len(self.results),
            "completed": sum(1 for r in self.results if r.status == ExperimentStatus.COMPLETED),
            "failed": sum(1 for r in self.results if r.status == ExperimentStatus.FAILED),
            "experiments": [r.to_dict() for r in self.results],
        }
        
        # Calculate aggregate metrics
        if self.results:
            report["average_duration_seconds"] = [
                (r.end_time - r.start_time).total_seconds()
                for r in self.results
                if r.end_time
            ]
        
        return report
    
    def save_report(self, output_path: Optional[Path] = None) -> None:
        """Save summary report to JSON."""
        if output_path is None:
            output_path = self.output_dir / "summary_report.json"
        
        report = self.generate_report()
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Saved summary report to {output_path}")
