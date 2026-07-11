"""
Persistent storage for experiment results with reproducibility guarantees.
"""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """Result of a single experiment trial."""
    
    experiment_id: str
    trial_id: int
    seed: int
    timestamp: str
    
    # Metrics
    success: bool
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    latency_seconds: Optional[float] = None
    token_usage: Optional[int] = None
    cost_usd: Optional[float] = None
    
    # Additional metrics
    custom_metrics: Dict[str, Any] = None
    
    # Error information
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    def __post_init__(self):
        if self.custom_metrics is None:
            self.custom_metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class ResultStore:
    """Store and retrieve experiment results with reproducibility guarantees."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.results_dir = output_dir / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_dir = output_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def store_result(self, result: ExperimentResult) -> Path:
        """Store a single experiment result."""
        # Create experiment directory
        experiment_dir = self.results_dir / result.experiment_id
        experiment_dir.mkdir(exist_ok=True)
        
        # Store as JSON for human readability
        json_path = experiment_dir / f"trial_{result.trial_id}_seed_{result.seed}.json"
        with open(json_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        
        # Store as pickle for efficient loading
        pickle_path = experiment_dir / f"trial_{result.trial_id}_seed_{result.seed}.pkl"
        with open(pickle_path, "wb") as f:
            pickle.dump(result, f)
        
        logger.debug(f"Stored result for {result.experiment_id} trial {result.trial_id}")
        return json_path
    
    def load_results(
        self,
        experiment_id: str,
    ) -> List[ExperimentResult]:
        """Load all results for an experiment."""
        experiment_dir = self.results_dir / experiment_id
        
        if not experiment_dir.exists():
            return []
        
        results = []
        for pickle_path in experiment_dir.glob("*.pkl"):
            try:
                with open(pickle_path, "rb") as f:
                    result = pickle.load(f)
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to load {pickle_path}: {e}")
        
        # Sort by trial_id and seed
        results.sort(key=lambda r: (r.trial_id, r.seed))
        return results
    
    def store_metadata(
        self,
        experiment_id: str,
        metadata: Dict[str, Any],
    ) -> Path:
        """Store experiment metadata."""
        metadata_path = self.metadata_dir / f"{experiment_id}_metadata.json"
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return metadata_path
    
    def load_metadata(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Load experiment metadata."""
        metadata_path = self.metadata_dir / f"{experiment_id}_metadata.json"
        
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, "r") as f:
            return json.load(f)
    
    def get_experiment_ids(self) -> List[str]:
        """Get all experiment IDs."""
        if not self.results_dir.exists():
            return []
        
        return [d.name for d in self.results_dir.iterdir() if d.is_dir()]
    
    def compute_result_hash(self, result: ExperimentResult) -> str:
        """Compute hash of result for deduplication."""
        result_dict = result.to_dict()
        result_str = json.dumps(result_dict, sort_keys=True)
        return hashlib.sha256(result_str.encode()).hexdigest()
    
    def export_results_csv(
        self,
        experiment_id: str,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Export results to CSV."""
        import csv
        
        results = self.load_results(experiment_id)
        
        if output_path is None:
            output_path = self.output_dir / f"{experiment_id}_results.csv"
        
        if not results:
            logger.warning(f"No results to export for {experiment_id}")
            return output_path
        
        # Flatten custom metrics
        fieldnames = [
            "experiment_id", "trial_id", "seed", "timestamp",
            "success", "accuracy", "precision", "recall", "f1",
            "latency_seconds", "token_usage", "cost_usd",
            "error_message", "error_type",
        ]
        
        # Add custom metric keys
        custom_keys = set()
        for result in results:
            custom_keys.update(result.custom_metrics.keys())
        fieldnames.extend(sorted(custom_keys))
        
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row = result.to_dict()
                row.update(result.custom_metrics)
                writer.writerow(row)
        
        logger.info(f"Exported {len(results)} results to {output_path}")
        return output_path
