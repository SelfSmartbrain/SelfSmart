from __future__ import annotations
from typing import List
from pydantic import BaseModel
from src.config.logging import get_logger
from src.capability.transfer_learning_engine import TransferLearningRecord

logger = get_logger(__name__)

class CrossDomainEvaluation(BaseModel):
    domains_evaluated: int
    successful_transfers: int
    average_efficiency: float
    records: List[TransferLearningRecord]

    model_config = {"from_attributes": True}

async def evaluate_cross_domain_transfer(
    records: List[TransferLearningRecord],
    efficiency_threshold: float = 0.1
) -> CrossDomainEvaluation:
    logger.info("Evaluating cross domain transfer learning records")
    
    successful = [r for r in records if r.transfer_efficiency >= efficiency_threshold]
    avg_efficiency = sum(r.transfer_efficiency for r in records) / len(records) if records else 0.0
    
    return CrossDomainEvaluation(
        domains_evaluated=len(records),
        successful_transfers=len(successful),
        average_efficiency=avg_efficiency,
        records=records
    )
