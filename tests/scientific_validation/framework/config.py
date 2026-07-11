"""
Configuration for scientific validation experiments.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum


class ComponentType(Enum):
    """ModelX components for ablation studies."""
    MEMORY = "memory"
    CONCEPTS = "concepts"
    WORLD_MODEL = "world_model"
    GOVERNANCE = "governance"
    PLANNER = "planner"
    REFLECTION = "reflection"
    TOOL_SELECTION = "tool_selection"


@dataclass
class ValidationConfig:
    """Configuration for validation experiments."""
    
    # Output directories
    output_dir: Path = field(default_factory=lambda: Path("scientific_validation_results"))
    data_dir: Path = field(default_factory=lambda: Path("scientific_validation_data"))
    
    # Experiment settings
    num_trials: int = 1000  # Number of independent trials per experiment
    num_seeds: int = 20  # Number of random seeds for reproducibility
    timeout_seconds: int = 3600  # Timeout for individual experiments
    
    # Statistical settings
    confidence_level: float = 0.95  # For confidence intervals
    bootstrap_samples: int = 10000  # For bootstrap confidence intervals
    min_effect_size: float = 0.2  # Cohen's d threshold for meaningful effect
    
    # Component initialization
    require_production_components: bool = True  # Fail if production components unavailable
    allow_fallback: bool = False  # Never use fallback implementations
    
    # Dataset settings
    dataset_size: int = 1000  # Tasks per dataset category
    dataset_cache: bool = True  # Cache generated datasets
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    
    # Parallel execution
    max_workers: int = 4  # Parallel experiment execution
    
    # Memory settings
    max_memory_mb: int = 8192
    
    def __post_init__(self):
        """Create directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "output_dir": str(self.output_dir),
            "data_dir": str(self.data_dir),
            "num_trials": self.num_trials,
            "num_seeds": self.num_seeds,
            "timeout_seconds": self.timeout_seconds,
            "confidence_level": self.confidence_level,
            "bootstrap_samples": self.bootstrap_samples,
            "min_effect_size": self.min_effect_size,
            "require_production_components": self.require_production_components,
            "allow_fallback": self.allow_fallback,
            "dataset_size": self.dataset_size,
            "dataset_cache": self.dataset_cache,
            "log_level": self.log_level,
            "max_workers": self.max_workers,
            "max_memory_mb": self.max_memory_mb,
        }
