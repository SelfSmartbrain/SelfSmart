"""future_simulator.py

Simulates future states under different scenarios.
Projects outcomes of decisions over time.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.config.logging import get_logger
from src.decision.scenario_generator import Scenario

logger = get_logger(__name__)


@dataclass
class SimulationState:
    """A state in the simulation."""
    time_step: int
    state_variables: Dict[str, float]
    events: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_step": self.time_step,
            "state_variables": self.state_variables,
            "events": self.events,
            "metadata": self.metadata,
        }


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    scenario_id: str
    scenario_name: str
    initial_state: SimulationState
    final_state: SimulationState
    state_history: List[SimulationState]
    outcome_metrics: Dict[str, float]
    success: bool
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "initial_state": self.initial_state.to_dict(),
            "final_state": self.final_state.to_dict(),
            "state_history": [s.to_dict() for s in self.state_history],
            "outcome_metrics": self.outcome_metrics,
            "success": self.success,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class FutureSimulator:
    """Simulates future states under different scenarios."""
    
    def __init__(self):
        self.simulation_models = {}
        logger.info("FutureSimulator initialized")
    
    def simulate(
        self,
        scenario: Scenario,
        action: Dict[str, Any],
        initial_state: Dict[str, float],
        time_steps: int = 10,
    ) -> SimulationResult:
        """Simulate the future under a given scenario."""
        logger.info(f"Simulating scenario: {scenario.name}")
        
        # Initialize simulation
        current_state = SimulationState(
            time_step=0,
            state_variables=initial_state.copy(),
        )
        
        state_history = [current_state]
        
        # Run simulation
        for step in range(1, time_steps + 1):
            next_state = self._step_simulation(
                current_state,
                action,
                scenario,
                step,
            )
            state_history.append(next_state)
            current_state = next_state
        
        # Calculate outcome metrics
        outcome_metrics = self._calculate_outcome_metrics(state_history)
        
        # Determine success
        success = self._determine_success(outcome_metrics, scenario)
        
        # Calculate confidence
        confidence = self._calculate_confidence(state_history, scenario)
        
        result = SimulationResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            initial_state=state_history[0],
            final_state=state_history[-1],
            state_history=state_history,
            outcome_metrics=outcome_metrics,
            success=success,
            confidence=confidence,
        )
        
        logger.info(f"Simulation complete for scenario: {scenario.name}")
        return result
    
    def _step_simulation(
        self,
        current_state: SimulationState,
        action: Dict[str, Any],
        scenario: Scenario,
        time_step: int,
    ) -> SimulationState:
        """Advance the simulation by one time step."""
        new_variables = current_state.state_variables.copy()
        events = []
        
        # Apply scenario parameters
        scenario_params = scenario.parameters
        
        # Simple simulation model: variables evolve based on action and scenario
        for var_name, var_value in new_variables.items():
            # Apply action effect
            action_effect = action.get("effect", {}).get(var_name, 0.0)
            
            # Apply scenario modifier
            scenario_modifier = scenario_params.get(f"{var_name}_modifier", 1.0)
            
            # Add some noise based on scenario type
            noise = self._generate_noise(scenario)
            
            # Update variable
            new_value = var_value + action_effect * scenario_modifier + noise
            new_variables[var_name] = max(0.0, min(1.0, new_value))  # Clamp to [0, 1]
        
        # Check for events
        if self._check_for_events(new_variables, scenario):
            events.append("Significant change detected")
        
        return SimulationState(
            time_step=time_step,
            state_variables=new_variables,
            events=events,
        )
    
    def _generate_noise(self, scenario: Scenario) -> float:
        """Generate noise based on scenario type."""
        import random
        
        if scenario.scenario_type.value == "optimistic":
            return random.uniform(-0.05, 0.1)
        elif scenario.scenario_type.value == "pessimistic":
            return random.uniform(-0.1, 0.05)
        elif scenario.scenario_type.value == "stress_test":
            return random.uniform(-0.2, 0.1)
        elif scenario.scenario_type.value == "black_swan":
            return random.uniform(-0.3, 0.2)
        else:  # baseline
            return random.uniform(-0.05, 0.05)
    
    def _check_for_events(
        self,
        state_variables: Dict[str, float],
        scenario: Scenario,
    ) -> bool:
        """Check if any significant events occur."""
        # Simple heuristic: if any variable changes significantly
        return any(abs(v) > 0.5 for v in state_variables.values())
    
    def _calculate_outcome_metrics(
        self,
        state_history: List[SimulationState],
    ) -> Dict[str, float]:
        """Calculate outcome metrics from simulation history."""
        if not state_history:
            return {}
        
        final_state = state_history[-1].state_variables
        
        metrics = {
            "final_state": final_state,
            "average_state": {},
            "improvement": {},
        }
        
        # Calculate average state
        all_vars = set()
        for state in state_history:
            all_vars.update(state.state_variables.keys())
        
        for var in all_vars:
            values = [s.state_variables.get(var, 0.0) for s in state_history]
            metrics["average_state"][var] = sum(values) / len(values)
        
        # Calculate improvement
        initial_state = state_history[0].state_variables
        for var in all_vars:
            initial = initial_state.get(var, 0.0)
            final = final_state.get(var, 0.0)
            metrics["improvement"][var] = final - initial
        
        return metrics
    
    def _determine_success(
        self,
        outcome_metrics: Dict[str, float],
        scenario: Scenario,
    ) -> bool:
        """Determine if the simulation was successful."""
        improvement = outcome_metrics.get("improvement", {})
        
        # Simple heuristic: success if average improvement is positive
        if improvement:
            avg_improvement = sum(improvement.values()) / len(improvement)
            return avg_improvement > 0.0
        
        return False
    
    def _calculate_confidence(
        self,
        state_history: List[SimulationState],
        scenario: Scenario,
    ) -> float:
        """Calculate confidence in the simulation result."""
        # Confidence based on scenario probability and stability
        base_confidence = scenario.probability
        
        # Adjust for stability (less variance = higher confidence)
        if len(state_history) > 1:
            variances = []
            all_vars = set()
            for state in state_history:
                all_vars.update(state.state_variables.keys())
            
            for var in all_vars:
                values = [s.state_variables.get(var, 0.0) for s in state_history]
                if len(values) > 1:
                    mean = sum(values) / len(values)
                    variance = sum((v - mean) ** 2 for v in values) / len(values)
                    variances.append(variance)
            
            if variances:
                avg_variance = sum(variances) / len(variances)
                stability_factor = 1.0 - min(1.0, avg_variance)
                base_confidence *= stability_factor
        
        return max(0.0, min(1.0, base_confidence))
    
    def compare_simulations(
        self,
        results: List[SimulationResult],
    ) -> Dict[str, Any]:
        """Compare multiple simulation results."""
        if not results:
            return {}
        
        comparison = {
            "total_simulations": len(results),
            "successful_count": sum(1 for r in results if r.success),
            "average_confidence": sum(r.confidence for r in results) / len(results),
            "scenario_comparison": [],
        }
        
        for result in results:
            comparison["scenario_comparison"].append({
                "scenario_name": result.scenario_name,
                "success": result.success,
                "confidence": result.confidence,
                "outcome_metrics": result.outcome_metrics,
            })
        
        return comparison
