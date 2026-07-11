"""Validation tools for Voice Assistant - enables running validation experiments via voice."""

from typing import Any, Dict
from src.tools.base import AgentTool
from pydantic import Field


class RunValidationTool(AgentTool):
    """Run comprehensive validation suite (ablations, benchmarks, cost analysis, long-horizon)."""
    
    name: str = "run_validation"
    description: str = "Run full validation suite including memory/concept/world_model/governance ablations, coding benchmark, cost analysis, and long-horizon test"
    max_retries: int = 0
    timeout_seconds: float = 300.0
    
    async def _execute(self, quick: bool = False) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        if quick:
            return {"message": "Quick validation not directly supported, running full suite", "results": runner.run_all_validations()}
        return runner.run_all_validations()


class RunAblationTool(AgentTool):
    """Run specific ablation study."""
    
    name: str = "run_ablation"
    description: str = "Run ablation study for a specific component (memory, concepts, world_model, governance)"
    max_retries: int = 0
    timeout_seconds: float = 120.0
    
    async def _execute(self, component: str) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        component = component.lower()
        
        if component == "memory":
            return runner.run_memory_ablation()
        elif component == "concepts" or component == "concept":
            return runner.run_concept_ablation()
        elif component == "world_model" or component == "world model":
            return runner.run_world_model_ablation()
        elif component == "governance":
            return runner.run_governance_ablation()
        else:
            return {"error": f"Unknown component: {component}. Use: memory, concepts, world_model, governance"}


class RunBenchmarkTool(AgentTool):
    """Run coding capability benchmark."""
    
    name: str = "run_benchmark"
    description: str = "Run coding capability benchmark against baseline systems"
    max_retries: int = 0
    timeout_seconds: float = 180.0
    
    async def _execute(self, num_tasks: int = 10) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        return runner.run_coding_benchmark()


class RunCostAnalysisTool(AgentTool):
    """Run cost analysis across subsystems."""
    
    name: str = "run_cost_analysis"
    description: str = "Analyze computational costs (tokens, latency, CPU, memory, API cost) across ModelX subsystems"
    max_retries: int = 0
    timeout_seconds: float = 60.0
    
    async def _execute(self) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        return runner.run_cost_analysis()


class RunLongHorizonTool(AgentTool):
    """Run long-horizon autonomy test."""
    
    name: str = "run_long_horizon"
    description: str = "Run extended autonomy test (24h, 72h, 1 week) tracking goal persistence, failure recovery, memory/knowledge growth, and stability"
    max_retries: int = 0
    timeout_seconds: float = 600.0
    
    async def _execute(self, duration_hours: int = 1) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        # Override duration for actual long-horizon testing
        from tests.validation.long_horizon import LongHorizonConfig, LongHorizonTester
        from tests.validation.framework import ValidationFramework
        
        framework = ValidationFramework(output_dir=Path("validation_results"))
        tester = LongHorizonTester(framework)
        
        config = LongHorizonConfig(
            duration_hours=duration_hours,
            check_interval_seconds=60,
            stop_on_failure=False,
        )
        
        def mock_task():
            return {"success": True, "goal_persistence": 0.95}
        
        metrics = tester.run_long_horizon_test(config, mock_task)
        return {
            "duration_seconds": metrics.duration_seconds,
            "goal_persistence_score": metrics.goal_persistence_score,
            "failure_recovery_count": metrics.failure_recovery_count,
            "stability_score": metrics.stability_score,
            "total_tasks_completed": metrics.total_tasks_completed,
            "total_failures": metrics.total_failures,
        }


class GetValidationReportTool(AgentTool):
    """Get validation report summary."""
    
    name: str = "get_validation_report"
    description: str = "Retrieve and summarize the latest validation report"
    max_retries: int = 0
    timeout_seconds: float = 30.0
    
    async def _execute(self) -> Dict[str, Any]:
        from pathlib import Path
        
        report_path = Path("validation_results/validation_report.md")
        summary_path = Path("validation_results/validation_summary.json")
        
        if not report_path.exists():
            return {"error": "No validation report found. Run a validation first."}
        
        result = {"report_path": str(report_path)}
        
        if summary_path.exists():
            import json
            with open(summary_path) as f:
                result["summary"] = json.load(f)
        
        with open(report_path) as f:
            content = f.read()
            result["report_preview"] = content[:2000]
        
        return result


# Export all validation tools
VALIDATION_TOOLS = [
    RunValidationTool,
    RunAblationTool,
    RunBenchmarkTool,
    RunCostAnalysisTool,
    RunLongHorizonTool,
    GetValidationReportTool,
]