from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional
from pydantic import BaseModel, Field
from src.config.logging import get_logger

logger = get_logger(__name__)

class TransferLearningRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_domain: str
    target_domain: str
    transfer_efficiency: float
    knowledge_retained: float
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}

async def calculate_transfer_learning(
    source_domain: str,
    target_domain: str,
    source_performance: float,
    target_performance_before: float,
    target_performance_after: float
) -> TransferLearningRecord:
    logger.info(f"Calculating transfer learning from {source_domain} to {target_domain}")
    
    improvement = target_performance_after - target_performance_before
    transfer_efficiency = improvement / source_performance if source_performance > 0 else 0.0
    knowledge_retained = target_performance_after / source_performance if source_performance > 0 else 0.0
    
    return TransferLearningRecord(
        source_domain=source_domain,
        target_domain=target_domain,
        transfer_efficiency=transfer_efficiency,
        knowledge_retained=knowledge_retained
    )
