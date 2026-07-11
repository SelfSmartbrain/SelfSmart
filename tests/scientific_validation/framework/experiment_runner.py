"""
Core experiment runner for scientific validation.
"""

import time
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import ValidationConfig
from .result_store import ResultStore, ExperimentResult
from .dataset_manager import DatasetManager, DatasetItem

logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment."""
    
    experiment_id: str
    name: str
    description: str
    
    # Dataset settings
    dataset_category: str
    dataset_size: int
    
    # Component settings
    components_enabled: Dict[str, bool]
    
    # Trial settings
    num_trials: int
    seeds: List[int]
    
    # Timeout
    timeout_seconds: int


class Experiment(ABC):
    """Abstract base class for validation experiments."""
    
    def __init__(
        self,
        config: ValidationConfig,
        result_store: ResultStore,
        dataset_manager: DatasetManager,
    ):
        self.config = config
        self.result_store = result_store
        self.dataset_manager = dataset_manager
    
    @abstractmethod
    def get_experiment_id(self) -> str:
        """Get unique experiment identifier."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get experiment name."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get experiment description."""
        pass
    
    @abstractmethod
    def setup(self) -> None:
        """Setup experiment (load components, datasets, etc.)."""
        pass
    
    @abstractmethod
    def execute_trial(
        self,
        trial_id: int,
        seed: int,
        dataset_item: DatasetItem,
        **kwargs,
    ) -> ExperimentResult:
        """Execute a single trial of the experiment."""
        pass
    
    @abstractmethod
    def teardown(self) -> None:
        """Cleanup after experiment."""
        pass
    
    def run(self, experiment_config: ExperimentConfig) -> List[ExperimentResult]:
        """Run the complete experiment."""
        logger.info(f"Starting experiment: {self.get_name()}")
        
        # Setup
        try:
            self.setup()
        except Exception as e:
            logger.error(f"Setup failed for {self.get_name()}: {e}")
            if self.config.require_production_components:
                raise
            logger.warning("Continuing despite setup failure (not recommended)")
        
        # Load dataset
        dataset = self.dataset_manager.get_or_generate_dataset(
            category=experiment_config.dataset_category,
            num_items=experiment_config.dataset_size,
            seed=experiment_config.seeds[0],  # Use first seed for dataset
        )
        
        # Store metadata
        metadata = {
            "experiment_id": self.get_experiment_id(),
            "name": self.get_name(),
            "description": self.get_description(),
            "config": experiment_config.__dict__,
            "dataset_size": len(dataset),
            "timestamp": time.time(),
        }
        self.result_store.store_metadata(self.get_experiment_id(), metadata)
        
        # Run trials
        results = []
        for trial_id, seed in enumerate(experiment_config.seeds):
            # Cycle through dataset items if more trials than items
            dataset_item = dataset[trial_id % len(dataset)]
            
            try:
                result = self.execute_trial(
                    trial_id=trial_id,
                    seed=seed,
                    dataset_item=dataset_item,
                    **experiment_config.components_enabled,
                )
                results.append(result)
                self.result_store.store_result(result)
                
                logger.debug(
                    f"Trial {trial_id} completed: success={result.success}, "
                    f"accuracy={result.accuracy}"
                )
            except Exception as e:
                logger.error(f"Trial {trial_id} failed: {e}")
                logger.debug(traceback.format_exc())
                
                # Store failure result
                failure_result = ExperimentResult(
                    experiment_id=self.get_experiment_id(),
                    trial_id=trial_id,
                    seed=seed,
                    timestamp=time.time(),
                    success=False,
                    error_message=str(e),
                    error_type=type(e).__name__,
                )
                results.append(failure_result)
                self.result_store.store_result(failure_result)
        
        # Teardown
        try:
            self.teardown()
        except Exception as e:
            logger.warning(f"Teardown failed: {e}")
        
        logger.info(f"Experiment {self.get_name()} completed: {len(results)} trials")
        return results


class ExperimentRunner:
    """Orchestrates multiple validation experiments."""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        
        self.result_store = ResultStore(config.output_dir)
        self.dataset_manager = DatasetManager(config.data_dir, config.dataset_cache)
        
        self.experiments: Dict[str, Experiment] = {}
    
    def register_experiment(self, experiment: Experiment) -> None:
        """Register an experiment."""
        experiment_id = experiment.get_experiment_id()
        self.experiments[experiment_id] = experiment
        logger.info(f"Registered experiment: {experiment_id}")
    
    def run_experiment(
        self,
        experiment_id: str,
        num_trials: Optional[int] = None,
        seeds: Optional[List[int]] = None,
    ) -> List[ExperimentResult]:
        """Run a specific experiment."""
        if experiment_id not in self.experiments:
            raise ValueError(f"Unknown experiment: {experiment_id}")
        
        experiment = self.experiments[experiment_id]
        
        # Generate seeds if not provided
        if seeds is None:
            num_seeds = num_trials or self.config.num_trials
            seeds = [random.randint(0, 2**31 - 1) for _ in range(num_seeds)]
        
        # Create experiment config
        experiment_config = ExperimentConfig(
            experiment_id=experiment_id,
            name=experiment.get_name(),
            description=experiment.get_description(),
            dataset_category=experiment_id,  # Use experiment_id as category
            dataset_size=num_trials or self.config.dataset_size,
            components_enabled={},  # Will be filled by experiment
            num_trials=len(seeds),
            seeds=seeds,
            timeout_seconds=self.config.timeout_seconds,
        )
        
        return experiment.run(experiment_config)
    
    def run_all_experiments(
        self,
        parallel: bool = True,
    ) -> Dict[str, List[ExperimentResult]]:
        """Run all registered experiments."""
        results = {}
        
        if parallel and self.config.max_workers > 1:
            # Run experiments in parallel
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = {
                    executor.submit(self.run_experiment, exp_id): exp_id
                    for exp_id in self.experiments.keys()
                }
                
                for future in as_completed(futures):
                    exp_id = futures[future]
                    try:
                        results[exp_id] = future.result()
                    except Exception as e:
                        logger.error(f"Experiment {exp_id} failed: {e}")
                        results[exp_id] = []
        else:
            # Run sequentially
            for exp_id in self.experiments.keys():
                try:
                    results[exp_id] = self.run_experiment(exp_id)
                except Exception as e:
                    logger.error(f"Experiment {exp_id} failed: {e}")
                    results[exp_id] = []
        
        return results
    
    def get_results(self, experiment_id: str) -> List[ExperimentResult]:
        """Get results for an experiment."""
        return self.result_store.load_results(experiment_id)
    
    def export_all_results_csv(self) -> Dict[str, Path]:
        """Export all experiment results to CSV."""
        export_paths = {}
        
        for exp_id in self.experiments.keys():
            try:
                path = self.result_store.export_results_csv(exp_id)
                export_paths[exp_id] = path
            except Exception as e:
                logger.warning(f"Failed to export {exp_id}: {e}")
        
        return export_paths
