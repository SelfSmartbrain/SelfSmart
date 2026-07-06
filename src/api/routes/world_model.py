from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config.logging import get_logger
from src.db.session import get_session

from src.db.models import (
    WorldModel,
    CausalRelationship,
    Hypothesis,
    Experiment,
    ExperimentRun,
    Evidence,
    BeliefState,
    Prediction,
    PredictionResult,
)

from src.api.schemas.world_model import (
    WorldModelCreate,
    WorldModelResponse,
    WorldModelUpdate,
    CausalRelationshipCreate,
    CausalRelationshipResponse,
    CausalRelationshipUpdate,
    HypothesisCreate,
    HypothesisResponse,
    HypothesisUpdate,
    ExperimentCreate,
    ExperimentResponse,
    ExperimentUpdate,
    ExperimentRunCreate,
    ExperimentRunResponse,
    ExperimentRunUpdate,
    EvidenceCreate,
    EvidenceResponse,
    EvidenceUpdate,
    BeliefStateCreate,
    BeliefStateResponse,
    BeliefStateUpdate,
    PredictionCreate,
    PredictionResponse,
    PredictionUpdate,
    PredictionResultCreate,
    PredictionResultResponse,
    PredictionResultUpdate,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/world-models", tags=["world_models"])


def get_or_404(obj, name: str):
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found")
    return obj


# -----------------------------------------------------------------------------
# World Models
# -----------------------------------------------------------------------------
@router.post("/", response_model=WorldModelResponse, status_code=status.HTTP_201_CREATED)
async def create_world_model(data: WorldModelCreate, session: AsyncSession = Depends(get_session)):
    db_obj = WorldModel(**data.model_dump())
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.get("/", response_model=List[WorldModelResponse])
async def list_world_models(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WorldModel).order_by(WorldModel.created_at.desc()))
    return result.scalars().all()


@router.get("/{model_id}", response_model=WorldModelResponse)
async def get_world_model(model_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WorldModel).where(WorldModel.id == model_id))
    return get_or_404(result.scalar_one_or_none(), "WorldModel")


@router.patch("/{model_id}", response_model=WorldModelResponse)
async def update_world_model(
    model_id: UUID, data: WorldModelUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(WorldModel).where(WorldModel.id == model_id))
    db_obj = get_or_404(result.scalar_one_or_none(), "WorldModel")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, key, value)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_world_model(model_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WorldModel).where(WorldModel.id == model_id))
    db_obj = get_or_404(result.scalar_one_or_none(), "WorldModel")
    await session.delete(db_obj)
    await session.commit()


# -----------------------------------------------------------------------------
# Causal Relationships
# -----------------------------------------------------------------------------
@router.post(
    "/causal-relationships",
    response_model=CausalRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_causal_relationship(
    data: CausalRelationshipCreate, session: AsyncSession = Depends(get_session)
):
    db_obj = CausalRelationship(**data.model_dump())
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.get("/causal-relationships/{rel_id}", response_model=CausalRelationshipResponse)
async def get_causal_relationship(rel_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(CausalRelationship).where(CausalRelationship.id == rel_id)
    )
    return get_or_404(result.scalar_one_or_none(), "CausalRelationship")


@router.patch("/causal-relationships/{rel_id}", response_model=CausalRelationshipResponse)
async def update_causal_relationship(
    rel_id: UUID, data: CausalRelationshipUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(CausalRelationship).where(CausalRelationship.id == rel_id)
    )
    db_obj = get_or_404(result.scalar_one_or_none(), "CausalRelationship")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, key, value)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.delete("/causal-relationships/{rel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_causal_relationship(rel_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(CausalRelationship).where(CausalRelationship.id == rel_id)
    )
    db_obj = get_or_404(result.scalar_one_or_none(), "CausalRelationship")
    await session.delete(db_obj)
    await session.commit()


# -----------------------------------------------------------------------------
# Hypotheses
# -----------------------------------------------------------------------------
@router.post("/hypotheses", response_model=HypothesisResponse, status_code=status.HTTP_201_CREATED)
async def create_hypothesis(data: HypothesisCreate, session: AsyncSession = Depends(get_session)):
    db_obj = Hypothesis(**data.model_dump())
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.get("/hypotheses/{hyp_id}", response_model=HypothesisResponse)
async def get_hypothesis(hyp_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Hypothesis).where(Hypothesis.id == hyp_id))
    return get_or_404(result.scalar_one_or_none(), "Hypothesis")


@router.patch("/hypotheses/{hyp_id}", response_model=HypothesisResponse)
async def update_hypothesis(
    hyp_id: UUID, data: HypothesisUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Hypothesis).where(Hypothesis.id == hyp_id))
    db_obj = get_or_404(result.scalar_one_or_none(), "Hypothesis")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, key, value)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.delete("/hypotheses/{hyp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hypothesis(hyp_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Hypothesis).where(Hypothesis.id == hyp_id))
    db_obj = get_or_404(result.scalar_one_or_none(), "Hypothesis")
    await session.delete(db_obj)
    await session.commit()


# -----------------------------------------------------------------------------
# Experiments
# -----------------------------------------------------------------------------
@router.post("/experiments", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(data: ExperimentCreate, session: AsyncSession = Depends(get_session)):
    db_obj = Experiment(**data.model_dump())
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.get("/experiments/{exp_id}", response_model=ExperimentResponse)
async def get_experiment(exp_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Experiment).where(Experiment.id == exp_id))
    return get_or_404(result.scalar_one_or_none(), "Experiment")


@router.patch("/experiments/{exp_id}", response_model=ExperimentResponse)
async def update_experiment(
    exp_id: UUID, data: ExperimentUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Experiment).where(Experiment.id == exp_id))
    db_obj = get_or_404(result.scalar_one_or_none(), "Experiment")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, key, value)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.delete("/experiments/{exp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(exp_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Experiment).where(Experiment.id == exp_id))
    db_obj = get_or_404(result.scalar_one_or_none(), "Experiment")
    await session.delete(db_obj)
    await session.commit()


# -----------------------------------------------------------------------------
# Experiment Runs
# -----------------------------------------------------------------------------
@router.post(
    "/experiment-runs", response_model=ExperimentRunResponse, status_code=status.HTTP_201_CREATED
)
async def create_experiment_run(
    data: ExperimentRunCreate, session: AsyncSession = Depends(get_session)
):
    db_obj = ExperimentRun(**data.model_dump())
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.get("/experiment-runs/{run_id}", response_model=ExperimentRunResponse)
async def get_experiment_run(run_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ExperimentRun).where(ExperimentRun.id == run_id))
    return get_or_404(result.scalar_one_or_none(), "ExperimentRun")


@router.patch("/experiment-runs/{run_id}", response_model=ExperimentRunResponse)
async def update_experiment_run(
    run_id: UUID, data: ExperimentRunUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(ExperimentRun).where(ExperimentRun.id == run_id))
    db_obj = get_or_404(result.scalar_one_or_none(), "ExperimentRun")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, key, value)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


# -----------------------------------------------------------------------------
# Evidence
# -----------------------------------------------------------------------------
@router.post("/evidence", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(data: EvidenceCreate, session: AsyncSession = Depends(get_session)):
    db_obj = Evidence(**data.model_dump())
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(evidence_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Evidence).where(Evidence.id == evidence_id))
    return get_or_404(result.scalar_one_or_none(), "Evidence")


# -----------------------------------------------------------------------------
# Belief States
# -----------------------------------------------------------------------------
@router.post(
    "/belief-states", response_model=BeliefStateResponse, status_code=status.HTTP_201_CREATED
)
async def create_belief_state(
    data: BeliefStateCreate, session: AsyncSession = Depends(get_session)
):
    db_obj = BeliefState(**data.model_dump())
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.get("/belief-states/{state_id}", response_model=BeliefStateResponse)
async def get_belief_state(state_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(BeliefState).where(BeliefState.id == state_id))
    return get_or_404(result.scalar_one_or_none(), "BeliefState")


# -----------------------------------------------------------------------------
# Predictions
# -----------------------------------------------------------------------------
@router.post("/predictions", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def create_prediction(data: PredictionCreate, session: AsyncSession = Depends(get_session)):
    db_obj = Prediction(**data.model_dump())
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.get("/predictions/{pred_id}", response_model=PredictionResponse)
async def get_prediction(pred_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Prediction).where(Prediction.id == pred_id))
    return get_or_404(result.scalar_one_or_none(), "Prediction")


# -----------------------------------------------------------------------------
# Prediction Results
# -----------------------------------------------------------------------------
@router.post(
    "/prediction-results",
    response_model=PredictionResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prediction_result(
    data: PredictionResultCreate, session: AsyncSession = Depends(get_session)
):
    db_obj = PredictionResult(**data.model_dump())
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


@router.get("/prediction-results/{result_id}", response_model=PredictionResultResponse)
async def get_prediction_result(result_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(PredictionResult).where(PredictionResult.id == result_id))
    return get_or_404(result.scalar_one_or_none(), "PredictionResult")
