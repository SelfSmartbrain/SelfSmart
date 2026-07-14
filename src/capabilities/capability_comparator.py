from __future__ import annotations
from typing import List, Dict
from uuid import UUID
from pydantic import BaseModel
from src.config.logging import get_logger

logger = get_logger(__name__)

class CapabilityDelta(BaseModel):
    capability_name: str
    model_a_id: UUID
    model_b_id: UUID
    score_a: float
    score_b: float
    delta: float

    model_config = {"from_attributes": True}

async def compare_capabilities(
    model_a_id: UUID, 
    model_b_id: UUID, 
    caps_a: Dict[str, float], 
    caps_b: Dict[str, float]
) -> List[CapabilityDelta]:
    logger.info(f"Comparing capabilities between {model_a_id} and {model_b_id}")
    deltas = []
    all_keys = set(caps_a.keys()).union(set(caps_b.keys()))
    for key in all_keys:
        score_a = caps_a.get(key, 0.0)
        score_b = caps_b.get(key, 0.0)
        deltas.append(CapabilityDelta(
            capability_name=key,
            model_a_id=model_a_id,
            model_b_id=model_b_id,
            score_a=score_a,
            score_b=score_b,
            delta=score_b - score_a
        ))
    return deltas
