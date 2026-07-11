from __future__ import annotations
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from src.config.logging import get_logger

logger = get_logger(__name__)

class Capability(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    category: str
    description: Optional[str] = None
    parameters: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}

class CapabilityInventory:
    """Inventory for internal capabilities available for mapping."""
    def __init__(self) -> None:
        self._capabilities: Dict[uuid.UUID, Capability] = {}

    async def add_capability(self, capability: Capability) -> Capability:
        """Add a new internal capability to the inventory."""
        self._capabilities[capability.id] = capability
        logger.info(f"Added capability: {capability.name} ({capability.id})")
        return capability

    async def get_capability(self, capability_id: uuid.UUID) -> Optional[Capability]:
        """Get capability by its ID."""
        return self._capabilities.get(capability_id)

    async def list_capabilities(self, category: Optional[str] = None) -> List[Capability]:
        """List available capabilities, optionally filtered by category."""
        if category:
            return [c for c in self._capabilities.values() if c.category == category]
        return list(self._capabilities.values())
        
    async def remove_capability(self, capability_id: uuid.UUID) -> bool:
        """Remove a capability from the inventory."""
        if capability_id in self._capabilities:
            del self._capabilities[capability_id]
            logger.info(f"Removed capability: {capability_id}")
            return True
        return False
