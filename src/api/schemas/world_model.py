from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorldModelBase(BaseModel):
    name: str
    description: Optional[str] = None


class WorldModelCreate(WorldModelBase):
    pass


class WorldModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WorldModelResponse(WorldModelBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class CausalRelationshipBase(BaseModel):
    world_model_id: UUID
    source_entity: str
    target_entity: str
    relationship_type: str
    confidence: float = 0.0


class CausalRelationshipCreate(CausalRelationshipBase):
    pass


class CausalRelationshipUpdate(BaseModel):
    source_entity: Optional[str] = None
    target_entity: Optional[str] = None
    relationship_type: Optional[str] = None
    confidence: Optional[float] = None


class CausalRelationshipResponse(CausalRelationshipBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class HypothesisBase(BaseModel):
    world_model_id: UUID
    description: str
    status: str = "proposed"


class HypothesisCreate(HypothesisBase):
    pass


class HypothesisUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None


class HypothesisResponse(HypothesisBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class ExperimentBase(BaseModel):
    hypothesis_id: UUID
    name: str
    description: Optional[str] = None
    setup_parameters: Optional[Dict[str, Any]] = None


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    setup_parameters: Optional[Dict[str, Any]] = None


class ExperimentResponse(ExperimentBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class ExperimentRunBase(BaseModel):
    experiment_id: UUID
    status: str = "pending"
    result_data: Optional[Dict[str, Any]] = None
    run_at: Optional[datetime] = None


class ExperimentRunCreate(ExperimentRunBase):
    pass


class ExperimentRunUpdate(BaseModel):
    status: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    run_at: Optional[datetime] = None


class ExperimentRunResponse(ExperimentRunBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class EvidenceBase(BaseModel):
    hypothesis_id: UUID
    experiment_run_id: Optional[UUID] = None
    description: str
    supports_hypothesis: bool
    weight: float = 1.0


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceUpdate(BaseModel):
    experiment_run_id: Optional[UUID] = None
    description: Optional[str] = None
    supports_hypothesis: Optional[bool] = None
    weight: Optional[float] = None


class EvidenceResponse(EvidenceBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class BeliefStateBase(BaseModel):
    world_model_id: UUID
    entity_name: str
    state_data: Dict[str, Any]
    confidence: float = 1.0


class BeliefStateCreate(BeliefStateBase):
    pass


class BeliefStateUpdate(BaseModel):
    entity_name: Optional[str] = None
    state_data: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None


class BeliefStateResponse(BeliefStateBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class PredictionBase(BaseModel):
    world_model_id: UUID
    target_entity: str
    predicted_state: Dict[str, Any]
    predicted_time: Optional[datetime] = None
    confidence: float = 1.0


class PredictionCreate(PredictionBase):
    pass


class PredictionUpdate(BaseModel):
    target_entity: Optional[str] = None
    predicted_state: Optional[Dict[str, Any]] = None
    predicted_time: Optional[datetime] = None
    confidence: Optional[float] = None


class PredictionResponse(PredictionBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class PredictionResultBase(BaseModel):
    prediction_id: UUID
    actual_state: Dict[str, Any]
    actual_time: datetime
    accuracy_score: Optional[float] = None


class PredictionResultCreate(PredictionResultBase):
    pass


class PredictionResultUpdate(BaseModel):
    actual_state: Optional[Dict[str, Any]] = None
    actual_time: Optional[datetime] = None
    accuracy_score: Optional[float] = None


class PredictionResultResponse(PredictionResultBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
