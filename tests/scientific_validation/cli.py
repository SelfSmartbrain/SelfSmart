#!/usr/bin/env python3
"""
CLI for running scientific validation experiments.

Usage:
    python -m tests.scientific_validation.cli run --experiment memory_ablation
    python -m tests.scientific_validation.cli run-all
    python -m tests.scientific_validation.cli report
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from framework.config import ValidationConfig
from framework.experiment_runner import ExperimentRunner
from framework.dataset_manager import DatasetManager
from datasets import (
    MemoryDatasetGenerator,
    ConceptDatasetGenerator,
    WorldModelDatasetGenerator,
    GovernanceDatasetGenerator,
    CodingDatasetGenerator,
    PlanningDatasetGenerator,
)
from experiments import (
    MemoryAblationExperiment,
    ConceptEngineExperiment,
    WorldModelExperiment,
    GovernanceExperiment,
    CodingBenchmarkExperiment,
    LongHorizonExperiment,
    AblationStudyExperiment,
)
from reports import ReportGenerator
from visualization import PlotGenerator, DashboardGenerator
from statistics import StatisticalTests, ConfidenceIntervals, EffectSizes


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None):
    """Setup logging configuration."""
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
    )


def register_datasets(dataset_manager: DatasetManager):
    """Register all dataset generators."""
    dataset_manager.register_generator(MemoryDatasetGenerator())
    dataset_manager.register_generator(ConceptDatasetGenerator())
    dataset_manager.register_generator(WorldModelDatasetGenerator())
    dataset_manager.register_generator(GovernanceDatasetGenerator())
    dataset_manager.register_generator(CodingDatasetGenerator())
    dataset_manager.register_generator(PlanningDatasetGenerator())


def register_experiments(
    runner: ExperimentRunner,
    config: ValidationConfig,
    result_store,
    dataset_manager: DatasetManager,
):
    """Register all experiments."""
    experiments = [
        MemoryAblationExperiment(config, result_store, dataset_manager),
        ConceptEngineExperiment(config, result_store, dataset_manager),
        WorldModelExperiment(config, result_store, dataset_manager),
        GovernanceExperiment(config, result_store, dataset_manager),
        CodingBenchmarkExperiment(config, result_store, dataset_manager),
        LongHorizonExperiment(config, result_store, dataset_manager),
        AblationStudyExperiment(config, result_store, dataset_manager),
    ]
    
    for experiment in experiments:
        runner.register_experiment(experiment)


def run_experiment(args):
    """Run a single experiment."""
    config = ValidationConfig(
        output_dir=Path(args.output_dir),
        data_dir=Path(args.data_dir),
        num_trials=args.trials,
        num_seeds=args.seeds,
        require_production_components=not args.allow_fallback,
        log_level=args.log_level,
    )
    
    setup_logging(config.log_level, config.log_file)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Running experiment: {args.experiment}")
    
    # Initialize components
    result_store = type('ResultStore', (), {
        'load_results': lambda exp_id: [],
        'store_result': lambda result: None,
        'store_metadata': lambda exp_id, metadata: None,
    })()
    
    dataset_manager = DatasetManager(config.data_dir, config.dataset_cache)
    register_datasets(dataset_manager)
    
    runner = ExperimentRunner(config)
    register_experiments(runner, config, result_store, dataset_manager)
    
    # Run the specified experiment
    try:
        results = runner.run_experiment(
            args.experiment,
            num_trials=args.trials,
        )
        logger.info(f"Experiment completed: {len(results)} trials")
    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        return 1
    
    return 0


def run_all_experiments(args):
    """Run all experiments."""
    config = ValidationConfig(
        output_dir=Path(args.output_dir),
        data_dir=Path(args.data_dir),
        num_trials=args.trials,
        num_seeds=args.seeds,
        require_production_components=not args.allow_fallback,
        log_level=args.log_level,
        parallel=not args.sequential,
    )
    
    setup_logging(config.log_level, config.log_file)
    
    logger = logging.getLogger(__name__)
    logger.info("Running all experiments")
    
    # Initialize components
    result_store = type('ResultStore', (), {
        'load_results': lambda exp_id: [],
        'store_result': lambda result: None,
        'store_metadata': lambda exp_id, metadata: None,
    })()
    
    dataset_manager = DatasetManager(config.data_dir, config.dataset_cache)
    register_datasets(dataset_manager)
    
    runner = ExperimentRunner(config)
    register_experiments(runner, config, result_store, dataset_manager)
    
    # Run all experiments
    try:
        results = runner.run_all_experiments(parallel=not args.sequential)
        logger.info(f"All experiments completed: {len(results)} experiments")
    except Exception as e:
        logger.error(f"Experiments failed: {e}")
        return 1
    
    return 0


def generate_report(args):
    """Generate validation report."""
    config = ValidationConfig(
        output_dir=Path(args.output_dir),
        data_dir=Path(args.data_dir),
    )
    
    setup_logging(args.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Generating validation report")
    
    # Load results from output directory
    results_dir = Path(args.output_dir) / "results"
    
    # Placeholder results - in real implementation, load from files
    results = {
        "experiments": {},
        "ablation": {},
        "statistics": {},
    }
    
    config_dict = config.to_dict()
    
    # Generate reports
    report_gen = ReportGenerator(config.output_dir)
    paths = report_gen.generate_all_formats(results, config_dict)
    
    logger.info(f"Generated reports: {paths}")
    return 0


def generate_visualizations(args):
    """Generate visualizations."""
    config = ValidationConfig(
        output_dir=Path(args.output_dir),
    )
    
    setup_logging(args.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Generating visualizations")
    
    # Generate plots
    plot_gen = PlotGenerator(config.output_dir)
    
    # Placeholder data - in real implementation, load from results
    experiment_results = {
        "memory_ablation": [0.8, 0.85, 0.9, 0.82, 0.88],
        "concept_engine": [0.75, 0.8, 0.78, 0.82, 0.85],
        "world_model": [0.7, 0.75, 0.72, 0.78, 0.8],
    }
    
    plot_gen.generate_accuracy_plot(experiment_results)
    
    # Generate dashboard
    dashboard_gen = DashboardGenerator(config.output_dir)
    dashboard_gen.generate_dashboard(results={"experiments": experiment_results})
    
    logger.info("Visualizations generated")
    return 0


def list_experiments(args):
    """List available experiments."""
    experiments = [
        "memory_ablation - Memory system ablation study",
        "concept_engine - Concept engine evaluation",
        "world_model - World model evaluation",
        "governance - Governance evaluation",
        "coding_benchmark - Coding capability benchmark",
        "long_horizon - Long horizon autonomy test",
        "ablation_study - Component ablation study",
    ]
    
    print("Available experiments:")
    for exp in experiments:
        print(f"  - {exp}")
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ModelX Scientific Validation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single experiment
  python -m tests.scientific_validation.cli run --experiment memory_ablation
  
  # Run all experiments
  python -m tests.scientific_validation.cli run-all
  
  # Generate reports
  python -m tests.scientific_validation.cli report
  
  # Generate visualizations
  python -m tests.scientific_validation.cli visualize
  
  # List available experiments
  python -m tests.scientific_validation.cli list
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a single experiment")
    run_parser.add_argument(
        "--experiment",
        required=True,
        choices=[
            "memory_ablation",
            "concept_engine",
            "world_model",
            "governance",
            "coding_benchmark",
            "long_horizon",
            "ablation_study",
        ],
        help="Experiment to run",
    )
    run_parser.add_argument(
        "--trials",
        type=int,
        default=100,
        help="Number of trials (default: 100)",
    )
    run_parser.add_argument(
        "--seeds",
        type=int,
        default=20,
        help="Number of random seeds (default: 20)",
    )
    run_parser.add_argument(
        "--output-dir",
        default="scientific_validation_results",
        help="Output directory (default: scientific_validation_results)",
    )
    run_parser.add_argument(
        "--data-dir",
        default="scientific_validation_data",
        help="Data directory (default: scientific_validation_data)",
    )
    run_parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Allow fallback implementations (not recommended)",
    )
    run_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    
    # Run-all command
    run_all_parser = subparsers.add_parser("run-all", help="Run all experiments")
    run_all_parser.add_argument(
        "--trials",
        type=int,
        default=100,
        help="Number of trials per experiment (default: 100)",
    )
    run_all_parser.add_argument(
        "--seeds",
        type=int,
        default=20,
        help="Number of random seeds (default: 20)",
    )
    run_all_parser.add_argument(
        "--output-dir",
        default="scientific_validation_results",
        help="Output directory (default: scientific_validation_results)",
    )
    run_all_parser.add_argument(
        "--data-dir",
        default="scientific_validation_data",
        help="Data directory (default: scientific_validation_data)",
    )
    run_all_parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Allow fallback implementations (not recommended)",
    )
    run_all_parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run experiments sequentially (default: parallel)",
    )
    run_all_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate validation report")
    report_parser.add_argument(
        "--output-dir",
        default="scientific_validation_results",
        help="Output directory (default: scientific_validation_results)",
    )
    report_parser.add_argument(
        "--data-dir",
        default="scientific_validation_data",
        help="Data directory (default: scientific_validation_data)",
    )
    report_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    
    # Visualize command
    viz_parser = subparsers.add_parser("visualize", help="Generate visualizations")
    viz_parser.add_argument(
        "--output-dir",
        default="scientific_validation_results",
        help="Output directory (default: scientific_validation_results)",
    )
    viz_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available experiments")
    
    args = parser.parse_args()
    
    if args.command == "run":
        return run_experiment(args)
    elif args.command == "run-all":
        return run_all_experiments(args)
    elif args.command == "report":
        return generate_report(args)
    elif args.command == "visualize":
        return generate_visualizations(args)
    elif args.command == "list":
        return list_experiments(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
