from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.world_model.hypothesis_generator import Hypothesis

logger = get_logger(__name__)

class ExperimentGroup(BaseModel):
    model_config = {"from_attributes": True}
    
    name: str
    conditions: Dict[str, Any]
    sample_size_target: int

class Experiment(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    hypothesis_id: uuid.UUID
    control_group: ExperimentGroup
    treatment_group: ExperimentGroup
    success_criteria: List[str]
    status: str = "designed"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ExperimentDesigner:
    def __init__(self):
        self.logger = get_logger(__name__)

    async def design_experiment(self, hypothesis: Hypothesis) -> Experiment:
        """
        Takes a Hypothesis and designs a control group, treatment group, and success criteria.
        """
        self.logger.info(f"Designing experiment for hypothesis {hypothesis.id}")
        
        control_group = ExperimentGroup(
            name="Control",
            conditions={"apply_pattern": False},
            sample_size_target=100
        )
        
        treatment_group = ExperimentGroup(
            name="Treatment",
            conditions={"apply_pattern": True},
            sample_size_target=100
        )
        
        success_criteria = [
            f"Treatment group shows >10% improvement in expected outcome: {hypothesis.expected_outcome}",
            "P-value < 0.05 for statistical significance"
        ]
        
        experiment = Experiment(
            hypothesis_id=hypothesis.id,
            control_group=control_group,
            treatment_group=treatment_group,
            success_criteria=success_criteria
        )
        
        self.logger.info(f"Designed experiment {experiment.id} with status {experiment.status}")
        return experiment
