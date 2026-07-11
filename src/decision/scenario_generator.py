"""scenario_generator.py

Generates scenarios for evaluating potential decisions.
Creates alternative futures to test decision robustness.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ScenarioType(str, Enum):
    """Types of scenarios."""
    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    BASELINE = "baseline"
    STRESS_TEST = "stress_test"
    BLACK_SWAN = "black_swan"


@dataclass
class Scenario:
    """A potential future scenario."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    scenario_type: ScenarioType = ScenarioType.BASELINE
    probability: float = 0.5
    parameters: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    time_horizon: str = "medium"  # short, medium, long
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type.value,
            "probability": self.probability,
            "parameters": self.parameters,
            "assumptions": self.assumptions,
            "time_horizon": self.time_horizon,
            "metadata": self.metadata,
        }


class ScenarioGenerator:
    """Generates scenarios for decision evaluation."""
    
    def __init__(self):
        self.scenario_templates = {
            ScenarioType.OPTIMISTIC: self._generate_optimistic_scenario,
            ScenarioType.PESSIMISTIC: self._generate_pessimistic_scenario,
            ScenarioType.BASELINE: self._generate_baseline_scenario,
            ScenarioType.STRESS_TEST: self._generate_stress_test_scenario,
            ScenarioType.BLACK_SWAN: self._generate_black_swan_scenario,
        }
        logger.info("ScenarioGenerator initialized")
    
    def generate_scenarios(
        self,
        context: Dict[str, Any],
        num_scenarios: int = 5,
        scenario_types: Optional[List[ScenarioType]] = None,
    ) -> List[Scenario]:
        """Generate scenarios for decision evaluation."""
        logger.info(f"Generating {num_scenarios} scenarios")
        
        if scenario_types is None:
            scenario_types = [
                ScenarioType.BASELINE,
                ScenarioType.OPTIMISTIC,
                ScenarioType.PESSIMISTIC,
                ScenarioType.STRESS_TEST,
            ]
        
        scenarios = []
        for i, scenario_type in enumerate(scenario_types[:num_scenarios]):
            generator = self.scenario_templates.get(scenario_type)
            if generator:
                scenario = generator(context, i)
                scenarios.append(scenario)
        
        # Fill remaining with baseline if needed
        while len(scenarios) < num_scenarios:
            scenario = self._generate_baseline_scenario(context, len(scenarios))
            scenarios.append(scenario)
        
        logger.info(f"Generated {len(scenarios)} scenarios")
        return scenarios
    
    def _generate_optimistic_scenario(
        self,
        context: Dict[str, Any],
        index: int,
    ) -> Scenario:
        """Generate an optimistic scenario."""
        return Scenario(
            name=f"Optimistic Scenario {index + 1}",
            description="Best-case outcome with favorable conditions",
            scenario_type=ScenarioType.OPTIMISTIC,
            probability=0.2,
            parameters={
                "success_rate": 0.9,
                "resource_availability": 1.2,
                "market_conditions": "favorable",
                "competition": "low",
            },
            assumptions=[
                "Resources are readily available",
                "Market conditions remain favorable",
                "No major disruptions occur",
            ],
        )
    
    def _generate_pessimistic_scenario(
        self,
        context: Dict[str, Any],
        index: int,
    ) -> Scenario:
        """Generate a pessimistic scenario."""
        return Scenario(
            name=f"Pessimistic Scenario {index + 1}",
            description="Worst-case outcome with adverse conditions",
            scenario_type=ScenarioType.PESSIMISTIC,
            probability=0.2,
            parameters={
                "success_rate": 0.3,
                "resource_availability": 0.7,
                "market_conditions": "adverse",
                "competition": "high",
            },
            assumptions=[
                "Resources are constrained",
                "Market conditions deteriorate",
                "Unexpected challenges arise",
            ],
        )
    
    def _generate_baseline_scenario(
        self,
        context: Dict[str, Any],
        index: int,
    ) -> Scenario:
        """Generate a baseline scenario."""
        return Scenario(
            name=f"Baseline Scenario {index + 1}",
            description="Expected outcome based on current trends",
            scenario_type=ScenarioType.BASELINE,
            probability=0.4,
            parameters={
                "success_rate": 0.6,
                "resource_availability": 1.0,
                "market_conditions": "stable",
                "competition": "moderate",
            },
            assumptions=[
                "Current trends continue",
                "Resources are as planned",
                "No major surprises",
            ],
        )
    
    def _generate_stress_test_scenario(
        self,
        context: Dict[str, Any],
        index: int,
    ) -> Scenario:
        """Generate a stress test scenario."""
        return Scenario(
            name=f"Stress Test Scenario {index + 1}",
            description="Extreme conditions to test robustness",
            scenario_type=ScenarioType.STRESS_TEST,
            probability=0.1,
            parameters={
                "success_rate": 0.4,
                "resource_availability": 0.5,
                "market_conditions": "volatile",
                "competition": "intense",
            },
            assumptions=[
                "Multiple simultaneous challenges",
                "Resource constraints",
                "High uncertainty",
            ],
        )
    
    def _generate_black_swan_scenario(
        self,
        context: Dict[str, Any],
        index: int,
    ) -> Scenario:
        """Generate a black swan scenario (rare, high-impact event)."""
        return Scenario(
            name=f"Black Swan Scenario {index + 1}",
            description="Rare, unpredictable, high-impact event",
            scenario_type=ScenarioType.BLACK_SWAN,
            probability=0.05,
            parameters={
                "success_rate": 0.1,
                "resource_availability": 0.3,
                "market_conditions": "disrupted",
                "competition": "unknown",
            },
            assumptions=[
                "Unprecedented event occurs",
                "Normal assumptions break down",
                "High uncertainty and volatility",
            ],
        )
    
    def generate_custom_scenario(
        self,
        name: str,
        description: str,
        scenario_type: ScenarioType,
        parameters: Dict[str, Any],
        assumptions: List[str],
        probability: float = 0.5,
    ) -> Scenario:
        """Generate a custom scenario."""
        return Scenario(
            name=name,
            description=description,
            scenario_type=scenario_type,
            parameters=parameters,
            assumptions=assumptions,
            probability=probability,
        )
