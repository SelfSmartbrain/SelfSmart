from __future__ import annotations

import uuid
import random
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.world_model.experiment_designer import Experiment

logger = get_logger(__name__)

class ExperimentRun(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    experiment_id: uuid.UUID
    control_results: Dict[str, Any]
    treatment_results: Dict[str, Any]
    p_value: float
    conclusion: str
    executed_at: datetime = Field(default_factory=datetime.utcnow)

class ExecutionLog(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID
    details: Dict[str, Any]
    outcome_metric: float

class ExperimentExecutor:
    def __init__(self):
        self.logger = get_logger(__name__)

    async def _gather_historical_evidence(self, conditions: Dict[str, Any], sample_size: int) -> List[ExecutionLog]:
        """
        Mocks gathering historical execution logs based on conditions.
        """
        self.logger.debug(f"Gathering {sample_size} historical logs for conditions: {conditions}")
        # Simulated log retrieval
        logs = []
        for _ in range(sample_size):
            # Base metric with some noise
            base = 50.0 if not conditions.get("apply_pattern") else 60.0
            logs.append(
                ExecutionLog(
                    id=uuid.uuid4(),
                    details=conditions,
                    outcome_metric=random.gauss(base, 10.0)
                )
            )
        return logs

    async def execute_experiment(self, experiment: Experiment) -> ExperimentRun:
        """
        Runs mock/simulated 'trials' using historical execution logs as evidence 
        to evaluate an experiment and produce an ExperimentRun.
        """
        self.logger.info(f"Executing experiment {experiment.id}")
        
        control_logs = await self._gather_historical_evidence(
            experiment.control_group.conditions, 
            experiment.control_group.sample_size_target
        )
        
        treatment_logs = await self._gather_historical_evidence(
            experiment.treatment_group.conditions,
            experiment.treatment_group.sample_size_target
        )
        
        control_mean = sum(log.outcome_metric for log in control_logs) / len(control_logs) if control_logs else 0.0
        treatment_mean = sum(log.outcome_metric for log in treatment_logs) / len(treatment_logs) if treatment_logs else 0.0
        
        # Mock statistical test
        difference = treatment_mean - control_mean
        p_value = 0.01 if difference > 5.0 else 0.45
        
        conclusion = "Hypothesis Validated: Significant improvement observed." if p_value < 0.05 else "Hypothesis Rejected: No significant improvement."
        
        run = ExperimentRun(
            experiment_id=experiment.id,
            control_results={"mean_outcome": control_mean, "samples": len(control_logs)},
            treatment_results={"mean_outcome": treatment_mean, "samples": len(treatment_logs)},
            p_value=p_value,
            conclusion=conclusion
        )
        
        self.logger.info(f"Experiment {experiment.id} executed with conclusion: {conclusion}")
        return run
