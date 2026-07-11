"""
Base report generator for scientific validation results.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Base class for generating validation reports."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_all_formats(
        self,
        results: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Path]:
        """Generate reports in all formats."""
        from .markdown_report import MarkdownReportGenerator
        from .json_report import JSONReportGenerator
        from .csv_report import CSVReportGenerator
        from .html_report import HTMLReportGenerator
        
        paths = {}
        
        # Markdown
        md_gen = MarkdownReportGenerator(self.output_dir)
        paths["markdown"] = md_gen.generate(results, config)
        
        # JSON
        json_gen = JSONReportGenerator(self.output_dir)
        paths["json"] = json_gen.generate(results, config)
        
        # CSV
        csv_gen = CSVReportGenerator(self.output_dir)
        paths["csv"] = csv_gen.generate(results, config)
        
        # HTML
        html_gen = HTMLReportGenerator(self.output_dir)
        paths["html"] = html_gen.generate(results, config)
        
        logger.info(f"Generated reports in {len(paths)} formats")
        return paths
    
    def _compute_summary_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compute summary statistics from results."""
        import numpy as np
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_experiments": len(results.get("experiments", {})),
            "total_trials": 0,
            "overall_success_rate": 0.0,
            "overall_accuracy": 0.0,
            "experiments": {},
        }
        
        all_accuracies = []
        all_successes = []
        
        for exp_name, exp_results in results.get("experiments", {}).items():
            if isinstance(exp_results, list):
                trial_count = len(exp_results)
                summary["total_trials"] += trial_count
                
                accuracies = [r.get("accuracy", 0) for r in exp_results if isinstance(r, dict)]
                successes = [r.get("success", False) for r in exp_results if isinstance(r, dict)]
                
                if accuracies:
                    summary["experiments"][exp_name] = {
                        "trials": trial_count,
                        "mean_accuracy": float(np.mean(accuracies)),
                        "std_accuracy": float(np.std(accuracies)),
                        "median_accuracy": float(np.median(accuracies)),
                        "success_rate": float(np.mean(successes)),
                    }
                    
                    all_accuracies.extend(accuracies)
                    all_successes.extend(successes)
        
        if all_accuracies:
            summary["overall_accuracy"] = float(np.mean(all_accuracies))
            summary["overall_success_rate"] = float(np.mean(all_successes))
        
        return summary
