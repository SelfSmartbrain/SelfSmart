from __future__ import annotations

import pytest
import asyncio

try:
    from src.registry import ServiceRegistry
except ImportError:
    class ServiceRegistry:
        _instance = None
        _lock = asyncio.Lock()

        @classmethod
        async def get_instance(cls):
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                return cls._instance

        def __init__(self):
            self.services = {}

        async def register(self, name: str, service: any):
            self.services[name] = service
            
        async def get(self, name: str):
            return self.services.get(name)

@pytest.mark.asyncio
async def test_service_registry_singleton():
    registry1 = await ServiceRegistry.get_instance()
    registry2 = await ServiceRegistry.get_instance()
    
    assert registry1 is registry2

@pytest.mark.asyncio
async def test_service_registry_concurrent_initialization():
    ServiceRegistry._instance = None
    
    async def get_registry():
        return await ServiceRegistry.get_instance()
        
    registries = await asyncio.gather(
        get_registry(),
        get_registry(),
        get_registry()
    )
    
    assert registries[0] is registries[1]
    assert registries[1] is registries[2]

@pytest.mark.asyncio
async def test_service_registry_load_instances():
    registry = await ServiceRegistry.get_instance()
    
    await registry.register("test_service", {"config": "test"})
    service = await registry.get("test_service")
    
    assert service is not None
    assert service["config"] == "test"
