"""
JSON report generator for scientific validation results.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging

from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class JSONReportGenerator(ReportGenerator):
    """Generate JSON reports for programmatic access."""
    
    def generate(
        self,
        results: Dict[str, Any],
        config: Dict[str, Any],
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate JSON report."""
        if output_path is None:
            output_path = self.output_dir / "validation_results.json"
        
        summary = self._compute_summary_statistics(results)
        
        json_content = {
            "metadata": {
                "timestamp": summary["timestamp"],
                "configuration": config,
            },
            "summary": summary,
            "experiments": results.get("experiments", {}),
            "ablation": results.get("ablation", {}),
            "statistics": results.get("statistics", {}),
        }
        
        with open(output_path, "w") as f:
            json.dump(json_content, f, indent=2, default=str)
        
        logger.info(f"Generated JSON report: {output_path}")
        return output_path
