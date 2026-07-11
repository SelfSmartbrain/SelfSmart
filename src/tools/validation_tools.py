"""
Validation Framework Tools for Voice Assistant
Provides LangChain-compatible tools for running validation experiments via voice.
"""

from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field

from src.tools.base import AgentTool


class RunValidationArgs(BaseModel):
    quick: bool = Field(default=False, description="Run quick validation with fewer trials")


class RunValidationTool(AgentTool):
    """Run comprehensive validation suite (all ablation studies, benchmarks, cost analysis, long-horizon)."""
    
    name: str = "run_validation"
    description: str = "Run the full Phase V2 validation suite including all ablation studies, coding benchmark, cost analysis, and long-horizon testing. Returns summary of key findings."
    args_schema: Type[BaseModel] = RunValidationArgs
    
    max_retries: int = 1
    
    async def _execute(self, quick: bool = False, **kwargs) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        import asyncio
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        summary = await asyncio.get_event_loop().run_in_executor(
            None, runner.run_all_validations
        )
        
        findings = summary.get("key_findings", [])
        
        return {
            "summary": summary,
            "findings": findings,
            "quick": quick
        }


class RunAblationArgs(BaseModel):
    component: str = Field(description="Component to ablate: memory, concepts, world_model, governance")


class RunAblationTool(AgentTool):
    """Run specific ablation study for a component."""
    
    name: str = "run_ablation"
    description: str = "Run ablation study for a specific ModelX component. Component options: memory, concepts, world_model, governance."
    args_schema: Type[BaseModel] = RunAblationArgs
    
    max_retries: int = 1
    
    async def _execute(self, component: str, **kwargs) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        import asyncio
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        
        method_map = {
            "memory": runner.run_memory_ablation,
            "concepts": runner.run_concept_ablation,
            "world_model": runner.run_world_model_ablation,
            "governance": runner.run_governance_ablation,
        }
        
        if component not in method_map:
            return {"error": f"Unknown component: {component}. Options: {list(method_map.keys())}"}
        
        result = await asyncio.get_event_loop().run_in_executor(
            None, method_map[component]
        )
        
        return {"component": component, **result}


class RunBenchmarkArgs(BaseModel):
    task_type: str = Field(default="all", description="Type of coding task to benchmark")


class RunBenchmarkTool(AgentTool):
    """Run coding capability benchmark."""
    
    name: str = "run_benchmark"
    description: str = "Run coding capability benchmark against task types: bug_fixing, feature_implementation, test_generation, refactoring, repository_analysis."
    args_schema: Type[BaseModel] = RunBenchmarkArgs
    
    max_retries: int = 1
    
    async def _execute(self, task_type: str = "all", **kwargs) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        import asyncio
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        result = await asyncio.get_event_loop().run_in_executor(
            None, runner.run_coding_benchmark
        )
        
        return {"task_type": task_type, **result}


class RunCostAnalysisTool(AgentTool):
    """Run cost analysis across ModelX subsystems."""
    
    name: str = "run_cost_analysis"
    description: str = "Analyze computational costs (tokens, latency, CPU, memory, API cost) across ModelX subsystems: memory, reasoning, world_model, governance."
    args_schema: Type[BaseModel] = type("RunCostAnalysisArgs", (BaseModel,), {})
    
    max_retries: int = 1
    
    async def _execute(self, **kwargs) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        import asyncio
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        result = await asyncio.get_event_loop().run_in_executor(
            None, runner.run_cost_analysis
        )
        
        return result


class RunLongHorizonArgs(BaseModel):
    duration_hours: int = Field(default=1, description="Test duration in hours (simulated)")


class RunLongHorizonTool(AgentTool):
    """Run long-horizon autonomy test."""
    
    name: str = "run_long_horizon"
    description: str = "Run extended autonomy test (24h, 72h, 1 week simulation) tracking goal persistence, failure recovery, memory growth, knowledge growth, and stability."
    args_schema: Type[BaseModel] = RunLongHorizonArgs
    
    max_retries: int = 1
    
    async def _execute(self, duration_hours: int = 1, **kwargs) -> Dict[str, Any]:
        from tests.validation.run_validation import ValidationRunner
        from pathlib import Path
        import asyncio
        
        runner = ValidationRunner(output_dir=Path("validation_results"))
        result = await asyncio.get_event_loop().run_in_executor(
            None, runner.run_long_horizon_test
        )
        
        return {"requested_duration_hours": duration_hours, **result}


class GetValidationReportTool(AgentTool):
    """Get the latest validation report."""
    
    name: str = "get_validation_report"
    description: str = "Retrieve the latest Phase V2 validation report with ablation results, benchmark scores, cost analysis, and long-horizon stability metrics."
    args_schema: Type[BaseModel] = type("GetValidationReportArgs", (BaseModel,), {})
    
    max_retries: int = 1
    
    async def _execute(self, **kwargs) -> Dict[str, Any]:
        from pathlib import Path
        import json
        
        report_path = Path("validation_results/validation_report.md")
        summary_path = Path("validation_results/validation_summary.json")
        
        if not report_path.exists():
            return {"error": "No validation report found. Run validation first."}
        
        with open(report_path, "r") as f:
            report = f.read()
        
        summary = {}
        if summary_path.exists():
            with open(summary_path, "r") as f:
                summary = json.load(f)
        
        return {
            "report": report[:3000],
            "summary": summary,
            "full_report_path": str(report_path)
        }