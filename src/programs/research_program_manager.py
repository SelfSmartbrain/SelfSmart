from __future__ import annotations

from typing import List, Optional, Dict
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.programs.long_horizon_program import LongHorizonProgram

logger = get_logger(__name__)

class ResearchProgramManager(BaseModel):
    model_config = {"from_attributes": True}
    
    active_programs: Dict[UUID, LongHorizonProgram] = Field(default_factory=dict)

    async def create_program(self, name: str, objective: str, duration_months: int) -> LongHorizonProgram:
        logger.info(f"Creating new research program: {name}")
        program = LongHorizonProgram(
            name=name,
            objective=objective,
            duration_months=duration_months
        )
        self.active_programs[program.program_id] = program
        return program

    async def get_program(self, program_id: UUID) -> Optional[LongHorizonProgram]:
        return self.active_programs.get(program_id)

    async def list_programs(self, status: Optional[str] = None) -> List[LongHorizonProgram]:
        if status:
            return [p for p in self.active_programs.values() if p.status == status]
        return list(self.active_programs.values())

    async def evaluate_progress(self, program_id: UUID) -> float:
        program = self.active_programs.get(program_id)
        if not program or not program.milestones:
            return 0.0
            
        completed = sum(1 for ms in program.milestones if ms.is_completed)
        progress = completed / len(program.milestones)
        logger.info(f"Program {program_id} progress: {progress * 100}%")
        return progress
