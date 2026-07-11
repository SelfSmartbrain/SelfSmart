from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GenomeTrait(BaseModel):
    model_config = {"from_attributes": True}

    name: str
    value: Any
    mutation_rate: float = Field(default=0.01)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    is_categorical: bool = False
    categories: Optional[List[str]] = None


class CognitiveGenomeData(BaseModel):
    model_config = {"from_attributes": True}

    traits: Dict[str, GenomeTrait] = Field(default_factory=dict)
    architecture_config: Dict[str, Any] = Field(default_factory=dict)
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    topology_definitions: Dict[str, Any] = Field(default_factory=dict)


class CognitiveGenomeCreate(BaseModel):
    generation_id: Optional[UUID] = None
    parent_ids: Optional[List[UUID]] = None
    genome_data: CognitiveGenomeData
    fitness_score: Optional[float] = None
    is_active: bool = True


class CognitiveGenomeResponse(CognitiveGenomeCreate):
    model_config = {"from_attributes": True}

    id: UUID
    created_at: datetime
    updated_at: datetime


class EvolutionGeneration(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    generation_number: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    metrics: Optional[Dict[str, Any]] = None


class GenomeMutationRecord(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    genome_id: UUID
    mutation_type: str
    mutation_details: Dict[str, Any]
    created_at: datetime
