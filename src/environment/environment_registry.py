from __future__ import annotations
import uuid
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from src.config.logging import get_logger

logger = get_logger(__name__)

class EnvironmentService(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    base_url: str
    description: Optional[str] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}

class EnvironmentRegistry:
    """Registry for managing available external environment services."""
    def __init__(self) -> None:
        self._services: Dict[uuid.UUID, EnvironmentService] = {}

    async def register_service(self, service: EnvironmentService) -> EnvironmentService:
        """Register a new environment service."""
        self._services[service.id] = service
        logger.info(f"Registered environment service: {service.name} ({service.id})")
        return service

    async def get_service(self, service_id: uuid.UUID) -> Optional[EnvironmentService]:
        """Retrieve an environment service by its ID."""
        return self._services.get(service_id)

    async def list_services(self) -> List[EnvironmentService]:
        """List all registered environment services."""
        return list(self._services.values())
        
    async def unregister_service(self, service_id: uuid.UUID) -> bool:
        """Unregister an environment service."""
        if service_id in self._services:
            del self._services[service_id]
            logger.info(f"Unregistered environment service: {service_id}")
            return True
        return False
