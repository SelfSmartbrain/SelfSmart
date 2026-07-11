from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.config.logging import get_logger

logger = get_logger(__name__)

class ArchitectureRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_version(self, version_name: str, metadata: Dict[str, Any] = None) -> uuid.UUID:
        metadata = metadata or {}
        
        query = text("""
            INSERT INTO architecture_versions (version, metadata_json)
            VALUES (:version, :metadata)
            RETURNING id
        """)
        
        result = await self.session.execute(
            query, 
            {"version": version_name, "metadata": metadata}
        )
        version_id = result.scalar_one()
        await self.session.commit()
        return version_id

    async def save_snapshot(self, version_id: uuid.UUID, snapshot_hash: str) -> uuid.UUID:
        query = text("""
            INSERT INTO architecture_snapshots (version_id, snapshot_hash)
            VALUES (:version_id, :snapshot_hash)
            RETURNING id
        """)
        
        result = await self.session.execute(
            query, 
            {"version_id": version_id, "snapshot_hash": snapshot_hash}
        )
        snapshot_id = result.scalar_one()
        await self.session.commit()
        return snapshot_id

    async def register_components(self, snapshot_id: uuid.UUID, components: list[Dict[str, Any]]) -> None:
        if not components:
            return
            
        query = text("""
            INSERT INTO architecture_components (snapshot_id, name, type, file_path)
            VALUES (:snapshot_id, :name, :type, :file_path)
        """)
        
        params = [
            {
                "snapshot_id": snapshot_id,
                "name": comp["name"],
                "type": comp["type"],
                "file_path": comp["file_path"]
            }
            for comp in components
        ]
        
        await self.session.execute(query, params)
        await self.session.commit()

    async def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        query = text("""
            SELECT id, version_id, snapshot_hash, created_at
            FROM architecture_snapshots
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        result = await self.session.execute(query)
        row = result.fetchone()
        
        if not row:
            return None
            
        return {
            "id": row.id,
            "version_id": row.version_id,
            "snapshot_hash": row.snapshot_hash,
            "created_at": row.created_at
        }
