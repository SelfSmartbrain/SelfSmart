"""utility_functions.py

Defines utility functions for evaluating outcomes.
Utility represents the value or desirability of different states.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from src.config.logging import get_logger

logger = get_logger(__name__)


class UtilityType(str, Enum):
    """Types of utility functions."""
    LINEAR = "linear"
    LOGARITHMIC = "logarithmic"
    EXPONENTIAL = "exponential"
    SIGMOID = "sigmoid"
    POWER = "power"
    CUSTOM = "custom"


@dataclass
class UtilityFunction:
    """A utility function mapping outcomes to utility values."""
    name: str
    utility_type: UtilityType
    parameters: Dict[str, float]
    domain: tuple[float, float] = (0.0, 1.0)
    description: str = ""
    
    def evaluate(self, value: float) -> float:
        """Evaluate the utility function at a given value."""
        value = max(self.domain[0], min(self.domain[1], value))
        
        if self.utility_type == UtilityType.LINEAR:
            return self._linear(value)
        elif self.utility_type == UtilityType.LOGARITHMIC:
            return self._logarithmic(value)
        elif self.utility_type == UtilityType.EXPONENTIAL:
            return self._exponential(value)
        elif self.utility_type == UtilityType.SIGMOID:
            return self._sigmoid(value)
        elif self.utility_type == UtilityType.POWER:
            return self._power(value)
        else:
            return value
    
    def _linear(self, value: float) -> float:
        """Linear utility: U(x) = a*x + b"""
        a = self.parameters.get("slope", 1.0)
        b = self.parameters.get("intercept", 0.0)
        return a * value + b
    
    def _logarithmic(self, value: float) -> float:
        """Logarithmic utility: U(x) = a*ln(b*x + c)"""
        a = self.parameters.get("scale", 1.0)
        b = self.parameters.get("base", 1.0)
        c = self.parameters.get("offset", 1.0)
        return a * np.log(b * value + c)
    
    def _exponential(self, value: float) -> float:
        """Exponential utility: U(x) = a*exp(b*x)"""
        a = self.parameters.get("scale", 1.0)
        b = self.parameters.get("rate", 1.0)
        return a * np.exp(b * value)
    
    def _sigmoid(self, value: float) -> float:
        """Sigmoid utility: U(x) = 1 / (1 + exp(-k*(x - x0)))"""
        k = self.parameters.get("steepness", 1.0)
        x0 = self.parameters.get("midpoint", 0.5)
        return 1.0 / (1.0 + np.exp(-k * (value - x0)))
    
    def _power(self, value: float) -> float:
        """Power utility: U(x) = x^a"""
        a = self.parameters.get("exponent", 1.0)
        return value ** a


class UtilityFunctions:
    """Collection of utility functions for decision-making."""
    
    def __init__(self):
        self.functions: Dict[str, UtilityFunction] = {}
        self._initialize_default_functions()
        logger.info("UtilityFunctions initialized")
    
    def _initialize_default_functions(self):
        """Initialize default utility functions."""
        # Risk-neutral (linear)
        self.functions["risk_neutral"] = UtilityFunction(
            name="Risk Neutral",
            utility_type=UtilityType.LINEAR,
            parameters={"slope": 1.0, "intercept": 0.0},
            description="Linear utility, risk-neutral",
        )
        
        # Risk-averse (logarithmic)
        self.functions["risk_averse"] = UtilityFunction(
            name="Risk Averse",
            utility_type=UtilityType.LOGARITHMIC,
            parameters={"scale": 1.0, "base": 1.0, "offset": 0.01},
            description="Logarithmic utility, risk-averse",
        )
        
        # Risk-seeking (exponential)
        self.functions["risk_seeking"] = UtilityFunction(
            name="Risk Seeking",
            utility_type=UtilityType.EXPONENTIAL,
            parameters={"scale": 0.1, "rate": 2.0},
            description="Exponential utility, risk-seeking",
        )
        
        # Sigmoid (diminishing returns)
        self.functions["diminishing_returns"] = UtilityFunction(
            name="Diminishing Returns",
            utility_type=UtilityType.SIGMOID,
            parameters={"steepness": 10.0, "midpoint": 0.5},
            description="Sigmoid utility, diminishing returns",
        )
        
        # Power (risk preference parameter)
        self.functions["power_utility"] = UtilityFunction(
            name="Power Utility",
            utility_type=UtilityType.POWER,
            parameters={"exponent": 0.5},
            description="Power utility with risk parameter",
        )
    
    def add_function(self, function: UtilityFunction) -> None:
        """Add a custom utility function."""
        self.functions[function.name] = function
        logger.info(f"Added utility function: {function.name}")
    
    def get_function(self, name: str) -> Optional[UtilityFunction]:
        """Get a utility function by name."""
        return self.functions.get(name)
    
    def evaluate(self, function_name: str, value: float) -> float:
        """Evaluate a utility function."""
        function = self.get_function(function_name)
        if function is None:
            raise ValueError(f"Utility function {function_name} not found")
        return function.evaluate(value)
    
    def expected_utility(
        self,
        function_name: str,
        outcomes: List[float],
        probabilities: List[float],
    ) -> float:
        """Calculate expected utility given outcomes and probabilities."""
        if len(outcomes) != len(probabilities):
            raise ValueError("Outcomes and probabilities must have same length")
        
        if abs(sum(probabilities) - 1.0) > 1e-6:
            raise ValueError("Probabilities must sum to 1.0")
        
        function = self.get_function(function_name)
        if function is None:
            raise ValueError(f"Utility function {function_name} not found")
        
        expected = sum(
            function.evaluate(outcome) * probability
            for outcome, probability in zip(outcomes, probabilities)
        )
        
        return expected
    
    def certainty_equivalent(
        self,
        function_name: str,
        outcomes: List[float],
        probabilities: List[float],
    ) -> float:
        """Calculate certainty equivalent of a gamble."""
        expected_utility = self.expected_utility(function_name, outcomes, probabilities)
        
        # Find value x such that U(x) = expected_utility
        function = self.get_function(function_name)
        
        # Simple binary search
        low, high = function.domain
        for _ in range(100):
            mid = (low + high) / 2
            if function.evaluate(mid) < expected_utility:
                low = mid
            else:
                high = mid
        
        return (low + high) / 2
    
    def risk_premium(
        self,
        function_name: str,
        outcomes: List[float],
        probabilities: List[float],
    ) -> float:
        """Calculate risk premium."""
        expected_value = sum(
            outcome * probability
            for outcome, probability in zip(outcomes, probabilities)
        )
        
        certainty_equivalent = self.certainty_equivalent(
            function_name, outcomes, probabilities
        )
        
        return expected_value - certainty_equivalent
    
    def list_functions(self) -> List[str]:
        """List all available utility functions."""
        return list(self.functions.keys())
