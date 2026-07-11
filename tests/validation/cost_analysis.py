"""Cost analysis infrastructure for ModelX subsystems."""

import time
from pathlib import Path
from typing import Dict, Any, List, Callable
from dataclasses import dataclass, field
import logging

from tests.validation.framework import ValidationFramework
from tests.validation.metrics import MetricsCollector, MetricType

logger = logging.getLogger(__name__)


@dataclass
class CostMetrics:
    """Cost metrics for a subsystem."""
    
    subsystem_name: str
    token_usage: int
    latency_seconds: float
    cpu_usage_percent: float
    memory_usage_mb: float
    api_cost_usd: float
    total_cost_usd: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostAnalyzer:
    """Analyze costs across ModelX subsystems."""
    
    def __init__(self, framework: ValidationFramework):
        self.framework = framework
        self.metrics = MetricsCollector()
        logger.info("Initialized CostAnalyzer")
    
    def measure_subsystem_cost(
        self,
        subsystem_name: str,
        subsystem_func: Callable,
    ) -> CostMetrics:
        """Measure cost of running a subsystem."""
        logger.info(f"Measuring cost for subsystem: {subsystem_name}")
        
        start_time = time.time()
        
        try:
            result = subsystem_func()
            token_usage = result.get("token_usage", 0)
            api_cost = result.get("api_cost", 0.0)
        except Exception as e:
            logger.error(f"Subsystem failed: {subsystem_name}", error=str(e))
            token_usage = 0
            api_cost = 0.0
        
        elapsed = time.time() - start_time
        
        # Placeholder values for CPU and memory (would use psutil in production)
        cpu_delta = 0.0
        memory_delta = 0.0
        
        # Calculate total cost (simplified model)
        # In reality, this would include more detailed cost calculations
        total_cost = api_cost + (elapsed * 0.0001)  # $0.0001 per second of compute
        
        cost_metrics = CostMetrics(
            subsystem_name=subsystem_name,
            token_usage=token_usage,
            latency_seconds=elapsed,
            cpu_usage_percent=cpu_delta,
            memory_usage_mb=memory_delta,
            api_cost_usd=api_cost,
            total_cost_usd=total_cost,
        )
        
        logger.info(
            f"Cost measured for {subsystem_name}: "
            f"${total_cost:.6f}, {elapsed:.3f}s, {token_usage} tokens"
        )
        
        return cost_metrics
    
    def compare_subsystem_costs(
        self,
        costs: List[CostMetrics],
    ) -> Dict[str, Any]:
        """Compare costs across multiple subsystems."""
        if not costs:
            return {}
        
        total_tokens = sum(c.token_usage for c in costs)
        total_latency = sum(c.latency_seconds for c in costs)
        total_cpu = sum(c.cpu_usage_percent for c in costs)
        total_memory = sum(c.memory_usage_mb for c in costs)
        total_cost = sum(c.total_cost_usd for c in costs)
        
        comparison = {
            "total_subsystems": len(costs),
            "total_tokens": total_tokens,
            "total_latency_seconds": total_latency,
            "average_latency_seconds": total_latency / len(costs),
            "total_cpu_usage_percent": total_cpu,
            "average_cpu_usage_percent": total_cpu / len(costs),
            "total_memory_usage_mb": total_memory,
            "average_memory_usage_mb": total_memory / len(costs),
            "total_api_cost_usd": sum(c.api_cost_usd for c in costs),
            "total_cost_usd": total_cost,
            "average_cost_usd": total_cost / len(costs),
            "subsystem_breakdown": [c.__dict__ for c in costs],
        }
        
        return comparison
    
    def identify_cost_bottlenecks(
        self,
        costs: List[CostMetrics],
    ) -> List[Dict[str, Any]]:
        """Identify subsystems with highest costs."""
        if not costs:
            return []
        
        bottlenecks = []
        
        # Sort by total cost
        sorted_costs = sorted(costs, key=lambda c: c.total_cost_usd, reverse=True)
        
        for cost in sorted_costs:
            if cost.total_cost_usd > 0:
                bottlenecks.append({
                    "subsystem": cost.subsystem_name,
                    "cost_usd": cost.total_cost_usd,
                    "token_usage": cost.token_usage,
                    "latency_seconds": cost.latency_seconds,
                })
        
        return bottlenecks
