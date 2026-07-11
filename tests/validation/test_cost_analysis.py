"""Cost analysis infrastructure for ModelX subsystems."""

import pytest
import time
from pathlib import Path
from typing import Dict, Any, List
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
        subsystem_func: callable,
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


@pytest.fixture
def validation_framework():
    """Create a validation framework for testing."""
    return ValidationFramework(output_dir=Path("test_validation_results"))


@pytest.fixture
def cost_analyzer(validation_framework):
    """Create a cost analyzer instance."""
    return CostAnalyzer(validation_framework)


def test_cost_analyzer_initialization(cost_analyzer):
    """Test that cost analyzer initializes correctly."""
    assert cost_analyzer is not None
    assert cost_analyzer.framework is not None
    assert cost_analyzer.metrics is not None


def test_measure_subsystem_cost(cost_analyzer):
    """Test measuring cost of a subsystem."""
    def mock_subsystem():
        """Mock subsystem function."""
        return {
            "token_usage": 1000,
            "api_cost": 0.01,
        }
    
    cost = cost_analyzer.measure_subsystem_cost("test_subsystem", mock_subsystem)
    
    assert cost.subsystem_name == "test_subsystem"
    assert cost.token_usage == 1000
    assert cost.api_cost_usd == 0.01
    assert cost.latency_seconds >= 0


def test_compare_subsystem_costs(cost_analyzer):
    """Test comparing costs across subsystems."""
    costs = [
        CostMetrics(
            subsystem_name="memory",
            token_usage=500,
            latency_seconds=0.5,
            cpu_usage_percent=10.0,
            memory_usage_mb=50.0,
            api_cost_usd=0.005,
            total_cost_usd=0.00505,
        ),
        CostMetrics(
            subsystem_name="reasoning",
            token_usage=2000,
            latency_seconds=1.0,
            cpu_usage_percent=20.0,
            memory_usage_mb=100.0,
            api_cost_usd=0.02,
            total_cost_usd=0.0201,
        ),
    ]
    
    comparison = cost_analyzer.compare_subsystem_costs(costs)
    
    assert comparison["total_subsystems"] == 2
    assert comparison["total_tokens"] == 2500
    assert comparison["total_latency_seconds"] == 1.5
    assert comparison["total_cost_usd"] > 0


def test_identify_cost_bottlenecks(cost_analyzer):
    """Test identifying cost bottlenecks."""
    costs = [
        CostMetrics(
            subsystem_name="cheap_subsystem",
            token_usage=100,
            latency_seconds=0.1,
            cpu_usage_percent=5.0,
            memory_usage_mb=10.0,
            api_cost_usd=0.001,
            total_cost_usd=0.00101,
        ),
        CostMetrics(
            subsystem_name="expensive_subsystem",
            token_usage=5000,
            latency_seconds=2.0,
            cpu_usage_percent=30.0,
            memory_usage_mb=200.0,
            api_cost_usd=0.05,
            total_cost_usd=0.0502,
        ),
    ]
    
    bottlenecks = cost_analyzer.identify_cost_bottlenecks(costs)
    
    assert len(bottlenecks) == 2
    assert bottlenecks[0]["subsystem"] == "expensive_subsystem"
    assert bottlenecks[0]["cost_usd"] > bottlenecks[1]["cost_usd"]


def test_cost_metrics_dataclass():
    """Test CostMetrics dataclass."""
    metrics = CostMetrics(
        subsystem_name="test",
        token_usage=1000,
        latency_seconds=1.0,
        cpu_usage_percent=10.0,
        memory_usage_mb=50.0,
        api_cost_usd=0.01,
        total_cost_usd=0.0101,
    )
    
    assert metrics.subsystem_name == "test"
    assert metrics.token_usage == 1000
    assert metrics.total_cost_usd == 0.0101
