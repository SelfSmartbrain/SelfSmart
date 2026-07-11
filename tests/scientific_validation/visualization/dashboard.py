"""
Dashboard generator for interactive visualization.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """Generate HTML dashboard for interactive visualization."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir / "dashboard"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_dashboard(
        self,
        results: Dict[str, Any],
        output_path: Optional[Path] = None,
    ) -> Path:
        """Generate interactive HTML dashboard."""
        if output_path is None:
            output_path = self.output_dir / "index.html"
        
        html_content = self._generate_html(results)
        
        with open(output_path, "w") as f:
            f.write(html_content)
        
        logger.info(f"Generated dashboard: {output_path}")
        return output_path
    
    def _generate_html(self, results: Dict[str, Any]) -> str:
        """Generate HTML content for dashboard."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ModelX Scientific Validation Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .chart-container {{
            margin: 20px 0;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #007bff;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .status-success {{
            color: #28a745;
            font-weight: bold;
        }}
        .status-failure {{
            color: #dc3545;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>ModelX Scientific Validation Dashboard</h1>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{len(results.get('experiments', {}))}</div>
                <div class="metric-label">Experiments Run</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{self._get_total_trials(results)}</div>
                <div class="metric-label">Total Trials</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{self._get_overall_accuracy(results):.2%}</div>
                <div class="metric-label">Overall Accuracy</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{self._get_total_components(results)}</div>
                <div class="metric-label">Components Tested</div>
            </div>
        </div>
        
        <h2>Experiment Results</h2>
        <div class="chart-container">
            <canvas id="accuracyChart"></canvas>
        </div>
        
        <h2>Detailed Results</h2>
        {self._generate_results_table(results)}
        
        <h2>Statistical Analysis</h2>
        {self._generate_statistics_section(results)}
    </div>
    
    <script>
        // Accuracy Chart
        const ctx = document.getElementById('accuracyChart').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(list(results.get('experiments', {}).keys()))},
                datasets: [{{
                    label: 'Accuracy',
                    data: {json.dumps([self._get_exp_accuracy(results, exp) for exp in results.get('experiments', {}).keys()])},
                    backgroundColor: 'rgba(0, 123, 255, 0.7)',
                    borderColor: 'rgba(0, 123, 255, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 1
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    def _get_total_trials(self, results: Dict[str, Any]) -> int:
        """Get total number of trials across all experiments."""
        total = 0
        for exp_results in results.get('experiments', {}).values():
            if isinstance(exp_results, list):
                total += len(exp_results)
        return total
    
    def _get_overall_accuracy(self, results: Dict[str, Any]) -> float:
        """Calculate overall accuracy across all experiments."""
        accuracies = []
        for exp_results in results.get('experiments', {}).values():
            if isinstance(exp_results, list):
                for result in exp_results:
                    if isinstance(result, dict) and 'accuracy' in result:
                        accuracies.append(result['accuracy'])
        return sum(accuracies) / len(accuracies) if accuracies else 0.0
    
    def _get_total_components(self, results: Dict[str, Any]) -> int:
        """Get total number of components tested."""
        components = set()
        for exp_data in results.get('experiments', {}).values():
            if isinstance(exp_data, dict) and 'components' in exp_data:
                components.update(exp_data['components'])
        return len(components)
    
    def _get_exp_accuracy(self, results: Dict[str, Any], exp_name: str) -> float:
        """Get accuracy for a specific experiment."""
        exp_results = results.get('experiments', {}).get(exp_name, [])
        if isinstance(exp_results, list):
            accuracies = [r.get('accuracy', 0) for r in exp_results if isinstance(r, dict)]
            return sum(accuracies) / len(accuracies) if accuracies else 0.0
        return 0.0
    
    def _generate_results_table(self, results: Dict[str, Any]) -> str:
        """Generate HTML table of results."""
        rows = []
        for exp_name, exp_results in results.get('experiments', {}).items():
            if isinstance(exp_results, list):
                success_count = sum(1 for r in exp_results if isinstance(r, dict) and r.get('success', False))
                total_count = len(exp_results)
                accuracy = self._get_exp_accuracy(results, exp_name)
                
                rows.append(f"""
                    <tr>
                        <td>{exp_name}</td>
                        <td>{success_count}/{total_count}</td>
                        <td>{accuracy:.2%}</td>
                        <td class="{'status-success' if accuracy > 0.5 else 'status-failure'}">
                            {'Pass' if accuracy > 0.5 else 'Fail'}
                        </td>
                    </tr>
                """)
        
        return f"""
            <table>
                <thead>
                    <tr>
                        <th>Experiment</th>
                        <th>Success Rate</th>
                        <th>Accuracy</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        """
    
    def _generate_statistics_section(self, results: Dict[str, Any]) -> str:
        """Generate statistics section."""
        return """
            <div class="chart-container">
                <p>Statistical analysis including confidence intervals, effect sizes, and significance tests will be displayed here.</p>
            </div>
        """
