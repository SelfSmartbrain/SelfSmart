from __future__ import annotations

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class DiscoveryInfo(BaseModel):
    model_config = {"from_attributes": True}
    
    discovery_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    novelty_score: float = 0.0
    impact_score: float = 0.0
    reuse_count: int = 0
    discovery_score: float = 0.0
    tags: List[str] = Field(default_factory=list)

class DiscoveryTracker(BaseModel):
    model_config = {"from_attributes": True}
    
    discoveries: Dict[UUID, DiscoveryInfo] = Field(default_factory=dict)

    async def add_discovery(self, name: str, description: str, tags: Optional[List[str]] = None) -> DiscoveryInfo:
        logger.info(f"Adding new discovery: {name}")
        discovery = DiscoveryInfo(
            name=name,
            description=description,
            tags=tags or []
        )
        self.discoveries[discovery.discovery_id] = discovery
        return discovery

    async def get_discovery(self, discovery_id: UUID) -> Optional[DiscoveryInfo]:
        return self.discoveries.get(discovery_id)

    async def update_scores(self, discovery_id: UUID, novelty: float, impact: float, reuse: int) -> Optional[DiscoveryInfo]:
        discovery = self.discoveries.get(discovery_id)
        if not discovery:
            logger.warning(f"Discovery {discovery_id} not found for score update")
            return None
        
        discovery.novelty_score = novelty
        discovery.impact_score = impact
        discovery.reuse_count = reuse
        # Calculate discovery scores based on novelty * impact * reuse
        discovery.discovery_score = novelty * impact * (1 + reuse)
        
        logger.info(f"Updated scores for discovery {discovery_id}. New score: {discovery.discovery_score}")
        return discovery
