"""
Plot generator for scientific validation results.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PlotGenerator:
    """Generate publication-quality plots for validation results."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir / "plots"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_accuracy_plot(
        self,
        experiment_results: Dict[str, List[float]],
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate accuracy comparison plot across experiments."""
        if output_path is None:
            output_path = self.output_dir / "accuracy_comparison.png"
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib not available, skipping plot generation")
            return output_path
        
        experiments = list(experiment_results.keys())
        accuracies = [np.mean(results) for results in experiment_results.values()]
        errors = [np.std(results) for results in experiment_results.values()]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(experiments, accuracies, yerr=errors, capsize=5, alpha=0.7)
        ax.set_ylabel('Accuracy')
        ax.set_title('Accuracy Comparison Across Experiments')
        ax.set_ylim(0, 1)
        ax.grid(axis='y', alpha=0.3)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated accuracy plot: {output_path}")
        return output_path
    
    def generate_latency_plot(
        self,
        latencies: List[float],
        experiment_name: str,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate latency distribution plot."""
        if output_path is None:
            output_path = self.output_dir / f"{experiment_name}_latency.png"
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib not available, skipping plot generation")
            return output_path
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(latencies, bins=30, alpha=0.7, edgecolor='black')
        ax.set_xlabel('Latency (seconds)')
        ax.set_ylabel('Frequency')
        ax.set_title(f'Latency Distribution: {experiment_name}')
        ax.grid(axis='y', alpha=0.3)
        
        # Add mean line
        mean_latency = np.mean(latencies)
        ax.axvline(mean_latency, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_latency:.3f}s')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated latency plot: {output_path}")
        return output_path
    
    def generate_ablation_plot(
        self,
        baseline_results: List[float],
        ablated_results: Dict[str, List[float]],
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate ablation study plot showing impact of each component."""
        if output_path is None:
            output_path = self.output_dir / "ablation_study.png"
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib not available, skipping plot generation")
            return output_path
        
        components = list(ablated_results.keys())
        baseline_mean = np.mean(baseline_results)
        
        ablated_means = [np.mean(results) for results in ablated_results.values()]
        impacts = [baseline_mean - mean for mean in ablated_means]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = ['red' if impact > 0 else 'green' for impact in impacts]
        bars = ax.bar(components, impacts, color=colors, alpha=0.7)
        
        ax.set_ylabel('Performance Impact')
        ax.set_title('Ablation Study: Component Impact on Performance')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.grid(axis='y', alpha=0.3)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated ablation plot: {output_path}")
        return output_path
    
    def generate_confidence_interval_plot(
        self,
        results: List[float],
        experiment_name: str,
        confidence_level: float = 0.95,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate confidence interval plot."""
        if output_path is None:
            output_path = self.output_dir / f"{experiment_name}_confidence_intervals.png"
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from scipy import stats
        except ImportError:
            logger.warning("Required libraries not available, skipping plot generation")
            return output_path
        
        mean = np.mean(results)
        std_error = stats.sem(results)
        
        alpha = 1 - confidence_level
        t_critical = stats.t.ppf(1 - alpha / 2, len(results) - 1)
        margin_of_error = t_critical * std_error
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot individual results
        ax.scatter(range(len(results)), results, alpha=0.5, label='Individual Trials')
        
        # Plot mean with confidence interval
        ax.axhline(mean, color='red', linestyle='-', linewidth=2, label=f'Mean: {mean:.3f}')
        ax.axhline(mean + margin_of_error, color='red', linestyle='--', linewidth=1, alpha=0.7)
        ax.axhline(mean - margin_of_error, color='red', linestyle='--', linewidth=1, alpha=0.7, label=f'{confidence_level*100:.0f}% CI')
        
        ax.fill_between(
            range(len(results)),
            mean - margin_of_error,
            mean + margin_of_error,
            color='red',
            alpha=0.2
        )
        
        ax.set_xlabel('Trial')
        ax.set_ylabel('Performance')
        ax.set_title(f'{experiment_name}: Mean with {confidence_level*100:.0f}% Confidence Interval')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated confidence interval plot: {output_path}")
        return output_path
    
    def generate_token_usage_plot(
        self,
        token_usages: Dict[str, List[int]],
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate token usage comparison plot."""
        if output_path is None:
            output_path = self.output_dir / "token_usage_comparison.png"
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib not available, skipping plot generation")
            return output_path
        
        experiments = list(token_usages.keys())
        mean_tokens = [np.mean(tokens) for tokens in token_usages.values()]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(experiments, mean_tokens, alpha=0.7)
        ax.set_ylabel('Average Token Usage')
        ax.set_title('Token Usage Comparison Across Experiments')
        ax.grid(axis='y', alpha=0.3)
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated token usage plot: {output_path}")
        return output_path
    
    def generate_roc_curve(
        self,
        fpr: List[float],
        tpr: List[float],
        auc: float,
        experiment_name: str,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate ROC curve plot."""
        if output_path is None:
            output_path = self.output_dir / f"{experiment_name}_roc_curve.png"
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available, skipping plot generation")
            return output_path
        
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.plot(fpr, tpr, linewidth=2, label=f'ROC Curve (AUC = {auc:.3f})')
        ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random Classifier')
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title(f'ROC Curve: {experiment_name}')
        ax.legend(loc='lower right')
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated ROC curve: {output_path}")
        return output_path
