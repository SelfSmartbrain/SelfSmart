"""
CSV report generator for scientific validation results.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import csv
import logging

from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class CSVReportGenerator(ReportGenerator):
    """Generate CSV reports for data analysis."""
    
    def generate(
        self,
        results: Dict[str, Any],
        config: Dict[str, Any],
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate CSV report."""
        if output_path is None:
            output_path = self.output_dir / "validation_results.csv"
        
        # Flatten results into CSV format
        rows = []
        
        for exp_name, exp_results in results.get("experiments", {}).items():
            if isinstance(exp_results, list):
                for result in exp_results:
                    if isinstance(result, dict):
                        row = {
                            "experiment": exp_name,
                            "trial_id": result.get("trial_id"),
                            "seed": result.get("seed"),
                            "success": result.get("success"),
                            "accuracy": result.get("accuracy"),
                            "precision": result.get("precision"),
                            "recall": result.get("recall"),
                            "f1": result.get("f1"),
                            "latency_seconds": result.get("latency_seconds"),
                            "token_usage": result.get("token_usage"),
                            "cost_usd": result.get("cost_usd"),
                        }
                        
                        # Add custom metrics
                        for key, value in result.get("custom_metrics", {}).items():
                            row[f"custom_{key}"] = value
                        
                        rows.append(row)
        
        # Write CSV
        if rows:
            fieldnames = list(rows[0].keys())
            
            with open(output_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        else:
            # Write empty CSV with headers
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["experiment", "trial_id", "seed", "success", "accuracy"])
        
        logger.info(f"Generated CSV report: {output_path}")
        return output_path
