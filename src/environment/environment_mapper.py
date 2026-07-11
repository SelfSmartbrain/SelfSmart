from __future__ import annotations
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.config.logging import get_logger

from src.environment.environment_registry import EnvironmentRegistry, EnvironmentService
from src.environment.capability_inventory import CapabilityInventory, Capability

logger = get_logger(__name__)

class ServiceMapping(BaseModel):
    mapping_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    service_id: uuid.UUID
    capability_id: uuid.UUID
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"from_attributes": True}

class EnvironmentMapper:
    """Mapper to link internal capabilities against external APIs/services."""
    def __init__(self, registry: EnvironmentRegistry, inventory: CapabilityInventory) -> None:
        self.registry = registry
        self.inventory = inventory
        self._mappings: List[ServiceMapping] = []

    async def map_capability_to_service(self, capability_id: uuid.UUID, service_id: uuid.UUID, metadata: Optional[Dict[str, Any]] = None) -> ServiceMapping:
        """Create a mapping between an internal capability and an external service."""
        service = await self.registry.get_service(service_id)
        capability = await self.inventory.get_capability(capability_id)
        
        if not service or not capability:
            raise ValueError("Service or Capability not found.")
            
        mapping = ServiceMapping(
            service_id=service_id,
            capability_id=capability_id,
            metadata=metadata or {}
        )
        self._mappings.append(mapping)
        logger.info(f"Mapped capability {capability.name} to service {service.name}")
        return mapping

    async def get_mappings_for_capability(self, capability_id: uuid.UUID) -> List[ServiceMapping]:
        """Retrieve mappings for a specific internal capability."""
        return [m for m in self._mappings if m.capability_id == capability_id]

    async def get_mappings_for_service(self, service_id: uuid.UUID) -> List[ServiceMapping]:
        """Retrieve mappings for a specific external service."""
        return [m for m in self._mappings if m.service_id == service_id]
