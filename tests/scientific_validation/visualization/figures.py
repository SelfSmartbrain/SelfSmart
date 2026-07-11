"""
Figure generator for publication-quality figures.
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FigureGenerator:
    """Generate publication-quality figures for papers."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir / "figures"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_comparison_figure(
        self,
        modelx_results: Dict[str, List[float]],
        baseline_results: Dict[str, List[float]],
        baseline_name: str = "Baseline",
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate comparison figure with ModelX vs baseline."""
        if output_path is None:
            output_path = self.output_dir / "modelx_vs_baseline.png"
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib not available, skipping figure generation")
            return output_path
        
        experiments = list(modelx_results.keys())
        x = np.arange(len(experiments))
        width = 0.35
        
        modelx_means = [np.mean(results) for results in modelx_results.values()]
        baseline_means = [np.mean(results) for results in baseline_results.values()]
        
        modelx_errors = [np.std(results) for results in modelx_results.values()]
        baseline_errors = [np.std(results) for results in baseline_results.values()]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars1 = ax.bar(x - width/2, modelx_means, width, yerr=modelx_errors, 
                       label='ModelX', capsize=5, alpha=0.8)
        bars2 = ax.bar(x + width/2, baseline_means, width, yerr=baseline_errors,
                       label=baseline_name, capsize=5, alpha=0.8)
        
        ax.set_ylabel('Performance')
        ax.set_title(f'ModelX vs {baseline_name} Performance Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels(experiments, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 1)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated comparison figure: {output_path}")
        return output_path
    
    def generate_ablation_heatmap(
        self,
        ablation_matrix: Dict[str, Dict[str, float]],
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate ablation study heatmap."""
        if output_path is None:
            output_path = self.output_dir / "ablation_heatmap.png"
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib not available, skipping figure generation")
            return output_path
        
        components = list(ablation_matrix.keys())
        tasks = list(next(iter(ablation_matrix.values())).keys())
        
        data = np.array([[ablation_matrix[comp][task] for task in tasks] for comp in components])
        
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        
        ax.set_xticks(np.arange(len(tasks)))
        ax.set_yticks(np.arange(len(components)))
        ax.set_xticklabels(tasks, rotation=45, ha='right')
        ax.set_yticklabels(components)
        
        # Add text annotations
        for i in range(len(components)):
            for j in range(len(tasks)):
                text = ax.text(j, i, f'{data[i, j]:.2f}',
                             ha="center", va="center", color="black", fontsize=8)
        
        ax.set_title('Ablation Study: Component Impact on Tasks')
        fig.colorbar(im, ax=ax, label='Performance')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated ablation heatmap: {output_path}")
        return output_path
    
    def generate_scatter_plot(
        self,
        x_values: List[float],
        y_values: List[float],
        x_label: str,
        y_label: str,
        title: str,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate scatter plot."""
        if output_path is None:
            output_path = self.output_dir / f"{title.lower().replace(' ', '_')}.png"
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib not available, skipping figure generation")
            return output_path
        
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.scatter(x_values, y_values, alpha=0.6, s=50)
        
        # Add trend line
        z = np.polyfit(x_values, y_values, 1)
        p = np.poly1d(z)
        ax.plot(x_values, p(x_values), "r--", alpha=0.8, linewidth=2)
        
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(title)
        ax.grid(alpha=0.3)
        
        # Add correlation coefficient
        correlation = np.corrcoef(x_values, y_values)[0, 1]
        ax.text(0.05, 0.95, f'Correlation: {correlation:.3f}',
                transform=ax.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated scatter plot: {output_path}")
        return output_path
    
    def generate_box_plot(
        self,
        data: Dict[str, List[float]],
        title: str,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate box plot for distribution comparison."""
        if output_path is None:
            output_path = self.output_dir / f"{title.lower().replace(' ', '_')}_boxplot.png"
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available, skipping figure generation")
            return output_path
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        box_data = list(data.values())
        labels = list(data.keys())
        
        bp = ax.boxplot(box_data, labels=labels, patch_artist=True)
        
        # Color the boxes
        colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
        for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_ylabel('Performance')
        ax.set_title(title)
        ax.grid(axis='y', alpha=0.3)
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated box plot: {output_path}")
        return output_path
