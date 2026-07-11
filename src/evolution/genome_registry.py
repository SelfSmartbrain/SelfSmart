from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import get_logger
from src.evolution.cognitive_genome import CognitiveGenomeCreate, CognitiveGenomeData, CognitiveGenomeResponse

logger = get_logger(__name__)


class GenomeRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_genome(self, genome: CognitiveGenomeCreate) -> CognitiveGenomeResponse:
        logger.info("Creating new cognitive genome")
        query = text("""
            INSERT INTO cognitive_genomes (generation_id, parent_ids, genome_data, fitness_score, is_active)
            VALUES (:generation_id, :parent_ids, :genome_data, :fitness_score, :is_active)
            RETURNING id, generation_id, parent_ids, genome_data, fitness_score, is_active, created_at, updated_at
        """)
        
        result = await self.session.execute(
            query,
            {
                "generation_id": genome.generation_id,
                "parent_ids": genome.parent_ids,
                "genome_data": genome.genome_data.model_dump(mode='json'),
                "fitness_score": genome.fitness_score,
                "is_active": genome.is_active
            }
        )
        row = result.fetchone()
        await self.session.commit()
        return CognitiveGenomeResponse.model_validate(row)

    async def get_genome(self, genome_id: UUID) -> Optional[CognitiveGenomeResponse]:
        query = text("""
            SELECT id, generation_id, parent_ids, genome_data, fitness_score, is_active, created_at, updated_at
            FROM cognitive_genomes
            WHERE id = :id
        """)
        result = await self.session.execute(query, {"id": genome_id})
        row = result.fetchone()
        if row:
            return CognitiveGenomeResponse.model_validate(row)
        return None

    async def update_fitness(self, genome_id: UUID, fitness_score: float) -> Optional[CognitiveGenomeResponse]:
        logger.info(f"Updating fitness for genome {genome_id} to {fitness_score}")
        query = text("""
            UPDATE cognitive_genomes
            SET fitness_score = :fitness_score, updated_at = now()
            WHERE id = :id
            RETURNING id, generation_id, parent_ids, genome_data, fitness_score, is_active, created_at, updated_at
        """)
        result = await self.session.execute(query, {"fitness_score": fitness_score, "id": genome_id})
        row = result.fetchone()
        
        if row:
            # Record fitness history
            hist_query = text("""
                INSERT INTO fitness_histories (genome_id, fitness_score, components)
                VALUES (:genome_id, :fitness_score, :components)
            """)
            await self.session.execute(hist_query, {
                "genome_id": genome_id,
                "fitness_score": fitness_score,
                "components": "{}"
            })
            await self.session.commit()
            return CognitiveGenomeResponse.model_validate(row)
        
        await self.session.rollback()
        return None

    async def list_active_genomes(self, limit: int = 100) -> List[CognitiveGenomeResponse]:
        query = text("""
            SELECT id, generation_id, parent_ids, genome_data, fitness_score, is_active, created_at, updated_at
            FROM cognitive_genomes
            WHERE is_active = true
            ORDER BY fitness_score DESC NULLS LAST, created_at DESC
            LIMIT :limit
        """)
        result = await self.session.execute(query, {"limit": limit})
        rows = result.fetchall()
        return [CognitiveGenomeResponse.model_validate(row) for row in rows]
