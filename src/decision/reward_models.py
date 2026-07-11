"""reward_models.py

Defines reward models for learning from outcomes.
Reward models capture what the system should optimize for.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.decision.utility_functions import UtilityFunctions

logger = get_logger(__name__)


class RewardType(str, Enum):
    """Types of reward models."""
    SCALAR = "scalar"
    VECTOR = "vector"
    HIERARCHICAL = "hierarchical"
    MULTI_OBJECTIVE = "multi_objective"


@dataclass
class RewardSignal:
    """A single reward signal."""
    name: str
    value: float
    weight: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def weighted_value(self) -> float:
        """Get the weighted value of this reward."""
        return self.value * self.weight


@dataclass
class RewardModel:
    """A reward model that defines what to optimize for."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    reward_type: RewardType = RewardType.SCALAR
    reward_signals: List[RewardSignal] = field(default_factory=list)
    aggregation_method: str = "weighted_sum"  # weighted_sum, max, min, product
    normalization_method: str = "none"  # none, min_max, z_score
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def compute_reward(self, observations: Dict[str, float]) -> float:
        """Compute reward from observations."""
        if not self.reward_signals:
            return 0.0
        
        # Map observations to reward signals
        values = []
        for signal in self.reward_signals:
            value = observations.get(signal.name, 0.0)
            values.append(signal.weighted_value())
        
        # Aggregate
        if self.aggregation_method == "weighted_sum":
            return sum(values)
        elif self.aggregation_method == "max":
            return max(values)
        elif self.aggregation_method == "min":
            return min(values)
        elif self.aggregation_method == "product":
            result = 1.0
            for v in values:
                result *= v
            return result
        else:
            return sum(values)
    
    def add_signal(self, signal: RewardSignal) -> None:
        """Add a reward signal to the model."""
        self.reward_signals.append(signal)
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "reward_type": self.reward_type.value,
            "reward_signals": [
                {
                    "name": s.name,
                    "value": s.value,
                    "weight": s.weight,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in self.reward_signals
            ],
            "aggregation_method": self.aggregation_method,
            "normalization_method": self.normalization_method,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class RewardModels:
    """Manages reward models for learning and optimization."""
    
    def __init__(self, utility_functions: Optional[UtilityFunctions] = None):
        self.utility_functions = utility_functions or UtilityFunctions()
        self.models: Dict[str, RewardModel] = {}
        self._initialize_default_models()
        logger.info("RewardModels initialized")
    
    def _initialize_default_models(self):
        """Initialize default reward models."""
        # Simple scalar reward
        scalar_model = RewardModel(
            name="Simple Scalar",
            description="Simple scalar reward model",
            reward_type=RewardType.SCALAR,
            reward_signals=[
                RewardSignal(name="success", value=1.0, weight=1.0),
                RewardSignal(name="failure", value=-1.0, weight=1.0),
            ],
            aggregation_method="weighted_sum",
        )
        self.models[scalar_model.id] = scalar_model
        
        # Multi-objective reward
        multi_model = RewardModel(
            name="Multi-Objective",
            description="Multi-objective reward model",
            reward_type=RewardType.MULTI_OBJECTIVE,
            reward_signals=[
                RewardSignal(name="accuracy", value=1.0, weight=0.4),
                RewardSignal(name="speed", value=1.0, weight=0.3),
                RewardSignal(name="cost", value=-1.0, weight=0.3),
            ],
            aggregation_method="weighted_sum",
        )
        self.models[multi_model.id] = multi_model
        
        # Hierarchical reward
        hierarchical_model = RewardModel(
            name="Hierarchical",
            description="Hierarchical reward model",
            reward_type=RewardType.HIERARCHICAL,
            reward_signals=[
                RewardSignal(name="primary_goal", value=1.0, weight=1.0),
                RewardSignal(name="secondary_goal", value=0.5, weight=0.5),
                RewardSignal(name="tertiary_goal", value=0.25, weight=0.25),
            ],
            aggregation_method="weighted_sum",
        )
        self.models[hierarchical_model.id] = hierarchical_model
    
    def create_model(
        self,
        name: str,
        description: str,
        reward_type: RewardType,
        reward_signals: List[RewardSignal],
        aggregation_method: str = "weighted_sum",
    ) -> RewardModel:
        """Create a new reward model."""
        model = RewardModel(
            name=name,
            description=description,
            reward_type=reward_type,
            reward_signals=reward_signals,
            aggregation_method=aggregation_method,
        )
        self.models[model.id] = model
        logger.info(f"Created reward model: {name}")
        return model
    
    def get_model(self, model_id: str) -> Optional[RewardModel]:
        """Get a reward model by ID."""
        return self.models.get(model_id)
    
    def update_model(self, model_id: str, updates: Dict[str, Any]) -> Optional[RewardModel]:
        """Update a reward model."""
        model = self.get_model(model_id)
        if model is None:
            return None
        
        for key, value in updates.items():
            if hasattr(model, key):
                setattr(model, key, value)
        
        model.updated_at = datetime.now(timezone.utc)
        logger.info(f"Updated reward model: {model_id}")
        return model
    
    def delete_model(self, model_id: str) -> bool:
        """Delete a reward model."""
        if model_id in self.models:
            del self.models[model_id]
            logger.info(f"Deleted reward model: {model_id}")
            return True
        return False
    
    def list_models(self) -> List[RewardModel]:
        """List all reward models."""
        return list(self.models.values())
    
    def compute_reward(
        self,
        model_id: str,
        observations: Dict[str, float],
    ) -> float:
        """Compute reward using a specific model."""
        model = self.get_model(model_id)
        if model is None:
            raise ValueError(f"Reward model {model_id} not found")
        
        return model.compute_reward(observations)
    
    def learn_from_outcome(
        self,
        model_id: str,
        outcome: Dict[str, Any],
        actual_reward: float,
    ) -> None:
        """Learn from an actual outcome to improve the model."""
        model = self.get_model(model_id)
        if model is None:
            return
        
        # Simple learning: adjust weights based on prediction error
        predicted_reward = model.compute_reward(outcome)
        error = actual_reward - predicted_reward
        
        # Adjust weights slightly
        learning_rate = 0.01
        for signal in model.reward_signals:
            if signal.name in outcome:
                signal.weight += learning_rate * error * outcome[signal.name]
                signal.weight = max(0.0, min(1.0, signal.weight))
        
        model.updated_at = datetime.now(timezone.utc)
        logger.info(f"Learned from outcome for model: {model_id}")
