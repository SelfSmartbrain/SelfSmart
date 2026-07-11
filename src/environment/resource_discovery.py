from __future__ import annotations
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.config.logging import get_logger

from src.environment.environment_registry import EnvironmentRegistry, EnvironmentService

logger = get_logger(__name__)

class DiscoveredResource(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    resource_type: str
    endpoints: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"from_attributes": True}

class ResourceDiscovery:
    """Discovers available resources from registered environments."""
    def __init__(self, registry: EnvironmentRegistry) -> None:
        self.registry = registry
        self._discovered_resources: List[DiscoveredResource] = []

    async def scan_environments(self) -> List[DiscoveredResource]:
        """
        Simulates scanning registered environment services for available resources.
        """
        logger.info("Starting resource discovery scan across registered environments...")
        services = await self.registry.list_services()
        
        discovered = []
        for service in services:
            # Simulate async discovery process per service
            await asyncio.sleep(0.1) 
            resource = DiscoveredResource(
                resource_type=f"compute_{service.name.lower()}",
                endpoints=[f"{service.base_url}/api/v1/compute"],
                metadata={"status": "available", "service_id": str(service.id)}
            )
            discovered.append(resource)
            self._discovered_resources.append(resource)
            logger.info(f"Discovered resource: {resource.resource_type} at {resource.endpoints}")
            
        return discovered

    async def get_discovered_resources(self, resource_type: Optional[str] = None) -> List[DiscoveredResource]:
        """Retrieve previously discovered resources."""
        if resource_type:
            return [r for r in self._discovered_resources if r.resource_type == resource_type]
        return self._discovered_resources
