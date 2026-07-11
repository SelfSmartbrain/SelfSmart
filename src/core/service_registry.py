"""
src/core/service_registry.py

Purpose:
Singleton Dependency Injection container with lazy loading, async lifecycle management,
and structured initialization of the Phase 7/7.5 cognitive engines and agents.

Dependencies:
- src.cognition.* (all Phase 7 modules)
- src.config.logging
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Type, TypeVar

from src.config.logging import get_logger

# Import cognition modules for type hinting and instantiation
from src.cognition.reflection_agent import CognitionReflectionAgent
from src.cognition.failure_analyzer import FailureAnalyzer
from src.cognition.meta_learning_engine import MetaLearningEngine
from src.cognition.strategy_synthesizer import StrategySynthesizer
from src.cognition.skill_discovery import SkillDiscovery
from src.cognition.self_improvement import SelfImprovementEngine
from src.cognition.cognitive_metrics import CognitiveMetricsCalculator
from src.cognition.intelligence_reporter import IntelligenceReporter
from src.cognition.learning_velocity import LearningVelocityTracker
from src.cognition.performance_tracker import PerformanceTracker

logger = get_logger(__name__)

T = TypeVar("T")

class ServiceRegistry:
    """
    Singleton Dependency Injection container.
    Provides lazy loading and async lifecycle management for platform services.
    """
    
    _instance: Optional["ServiceRegistry"] = None
    _lock: Optional[asyncio.Lock] = None
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized: bool = False
    
    @classmethod
    async def get_instance(cls) -> "ServiceRegistry":
        """Get the singleton instance of the service registry."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def initialize_all(self) -> None:
        """Initialize and cache all core cognitive services."""
        if self._initialized:
            return
            
        if self._lock is None:
            self._lock = asyncio.Lock()
            
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing Service Registry")
            
            # Base trackers
            self._services["performance_tracker"] = PerformanceTracker()
            self._services["learning_velocity"] = LearningVelocityTracker()
            
            # Core cognition
            self._services["reflection_agent"] = CognitionReflectionAgent()
            self._services["failure_analyzer"] = FailureAnalyzer()
            self._services["meta_learning"] = MetaLearningEngine()
            self._services["strategy_synthesizer"] = StrategySynthesizer()
            self._services["skill_discovery"] = SkillDiscovery()
            
            # High-level engines
            self._services["cognitive_metrics"] = CognitiveMetricsCalculator()
            self._services["self_improvement"] = SelfImprovementEngine()
            self._services["intelligence_reporter"] = IntelligenceReporter()
            
            # NOTE: KnowledgeGraphManager, CuriosityEngine, GoalGenerator, ResearchDirector,
            # and LongHorizonPlanner will be instantiated here as they are migrated to the registry.
            
            self._initialized = True
            logger.info("Service Registry initialized successfully", service_count=len(self._services))

    def get(self, service_name: str) -> Any:
        """Get a service by name."""
        if service_name not in self._services:
            raise KeyError(f"Service '{service_name}' not found in registry.")
        return self._services[service_name]
    
    def get_typed(self, service_type: Type[T]) -> T:
        """Get a service by its type."""
        for service in self._services.values():
            if isinstance(service, service_type):
                return service
        raise KeyError(f"Service of type '{service_type.__name__}' not found in registry.")

    async def shutdown(self) -> None:
        """Gracefully shutdown all services (placeholder for future cleanup logic)."""
        logger.info("Shutting down Service Registry")
        self._services.clear()
        self._initialized = False


# Helper function for FastAPI dependency injection
async def get_registry() -> ServiceRegistry:
    registry = await ServiceRegistry.get_instance()
    if not registry._initialized:
        await registry.initialize_all()
    return registry
