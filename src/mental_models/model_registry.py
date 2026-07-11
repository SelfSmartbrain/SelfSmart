"""model_registry.py

Registry for managing mental models, their usage, and performance.
Tracks which models work best in which contexts.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from .mental_models import MentalModel, ModelType, PrebuiltModels

logger = get_logger(__name__)


class ModelEntry(BaseModel):
    """Serializable entry for model storage."""
    id: str
    name: str
    description: str
    model_type: str
    domain: str
    steps: List[str]
    heuristics: List[str]
    success_rate: float
    usage_count: int
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelUsage(BaseModel):
    """Record of model usage."""
    model_id: str
    context: str
    success: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


class ModelRegistry:
    """Registry for managing mental models."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.models: Dict[str, MentalModel] = {}
        self.usage_history: List[ModelUsage] = []
        self.storage_path = Path(storage_path) if storage_path else Path(".data/mental_models")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_path / "index.json"
        self.usage_path = self.storage_path / "usage.json"
        
        self._load_index()
        self._load_usage()
        self._load_prebuilt()
        
        logger.info(f"ModelRegistry initialized with storage at {self.storage_path}")
    
    def _load_index(self):
        """Load model index from storage."""
        if self.index_path.exists():
            try:
                with open(self.index_path, "r") as f:
                    index = json.load(f)
                    for entry_data in index.get("models", []):
                        entry = ModelEntry(**entry_data)
                        model = MentalModel(
                            id=entry.id,
                            name=entry.name,
                            description=entry.description,
                            model_type=ModelType(entry.model_type),
                            domain=entry.domain,
                            steps=entry.steps,
                            heuristics=entry.heuristics,
                            success_rate=entry.success_rate,
                            usage_count=entry.usage_count,
                            created_at=datetime.fromisoformat(entry.created_at),
                            updated_at=datetime.fromisoformat(entry.updated_at),
                            metadata=entry.metadata,
                        )
                        self.models[model.id] = model
                logger.info(f"Loaded {len(self.models)} models from index")
            except Exception as e:
                logger.error(f"Failed to load model index: {e}")
    
    def _save_index(self):
        """Save model index to storage."""
        try:
            entries = [
                ModelEntry(
                    id=m.id,
                    name=m.name,
                    description=m.description,
                    model_type=m.model_type.value,
                    domain=m.domain,
                    steps=m.steps,
                    heuristics=m.heuristics,
                    success_rate=m.success_rate,
                    usage_count=m.usage_count,
                    created_at=m.created_at.isoformat(),
                    updated_at=m.updated_at.isoformat(),
                    metadata=m.metadata,
                )
                for m in self.models.values()
            ]
            index = {
                "models": [e.model_dump() for e in entries],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.index_path, "w") as f:
                json.dump(index, f, indent=2)
            logger.info("Saved model index")
        except Exception as e:
            logger.error(f"Failed to save model index: {e}")
    
    def _load_usage(self):
        """Load usage history from storage."""
        if self.usage_path.exists():
            try:
                with open(self.usage_path, "r") as f:
                    data = json.load(f)
                    self.usage_history = [
                        ModelUsage(**usage_data)
                        for usage_data in data.get("usage", [])
                    ]
                logger.info(f"Loaded {len(self.usage_history)} usage records")
            except Exception as e:
                logger.error(f"Failed to load usage history: {e}")
    
    def _save_usage(self):
        """Save usage history to storage."""
        try:
            data = {
                "usage": [u.model_dump() for u in self.usage_history],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.usage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage history: {e}")
    
    def _load_prebuilt(self):
        """Load prebuilt mental models if not already present."""
        prebuilt = PrebuiltModels.get_all_prebuilt()
        for model in prebuilt:
            if model.id not in self.models:
                self.models[model.id] = model
        logger.info(f"Loaded {len(prebuilt)} prebuilt models")
    
    def register_model(self, model: MentalModel) -> MentalModel:
        """Register a new mental model."""
        self.models[model.id] = model
        self._save_index()
        logger.info(f"Registered model: {model.name}")
        return model
    
    def get_model(self, model_id: str) -> Optional[MentalModel]:
        """Retrieve a model by ID."""
        return self.models.get(model_id)
    
    def find_model_by_name(self, name: str) -> Optional[MentalModel]:
        """Find a model by name."""
        name_lower = name.lower()
        for model in self.models.values():
            if name_lower in model.name.lower():
                return model
        return None
    
    def list_models(
        self,
        model_type: Optional[ModelType] = None,
        domain: Optional[str] = None,
        min_success_rate: float = 0.0,
    ) -> List[MentalModel]:
        """List models with optional filters."""
        models = list(self.models.values())
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if domain:
            models = [m for m in models if m.domain == domain]
        
        if min_success_rate > 0:
            models = [m for m in models if m.success_rate >= min_success_rate]
        
        return sorted(models, key=lambda m: m.usage_count, reverse=True)
    
    def record_usage(
        self,
        model_id: str,
        context: str,
        success: bool,
        notes: str = "",
    ) -> bool:
        """Record usage of a mental model."""
        if model_id not in self.models:
            return False
        
        usage = ModelUsage(
            model_id=model_id,
            context=context,
            success=success,
            notes=notes,
        )
        self.usage_history.append(usage)
        
        # Update model stats
        model = self.models[model_id]
        model.usage_count += 1
        
        # Update success rate with exponential moving average
        alpha = 0.1  # Learning rate
        new_success = 1.0 if success else 0.0
        model.success_rate = (1 - alpha) * model.success_rate + alpha * new_success
        model.updated_at = datetime.now(timezone.utc)
        
        self._save_index()
        self._save_usage()
        
        logger.info(f"Recorded usage for model {model_id}: success={success}")
        return True
    
    def get_model_performance(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get performance statistics for a model."""
        if model_id not in self.models:
            return None
        
        model = self.models[model_id]
        usages = [u for u in self.usage_history if u.model_id == model_id]
        
        if not usages:
            return {
                "model_id": model_id,
                "name": model.name,
                "usage_count": 0,
                "success_rate": model.success_rate,
                "recent_successes": 0,
                "recent_failures": 0,
            }
        
        recent_usages = usages[-20:]  # Last 20 uses
        recent_successes = sum(1 for u in recent_usages if u.success)
        recent_failures = len(recent_usages) - recent_successes
        
        return {
            "model_id": model_id,
            "name": model.name,
            "usage_count": model.usage_count,
            "success_rate": model.success_rate,
            "recent_successes": recent_successes,
            "recent_failures": recent_failures,
            "recent_success_rate": recent_successes / len(recent_usages) if recent_usages else 0.0,
        }
    
    def get_top_models(self, n: int = 10, model_type: Optional[ModelType] = None) -> List[MentalModel]:
        """Get top N models by success rate."""
        models = list(self.models.values())
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        return sorted(models, key=lambda m: m.success_rate, reverse=True)[:n]
    
    def update_model(
        self,
        model_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        steps: Optional[List[str]] = None,
        heuristics: Optional[List[str]] = None,
    ) -> Optional[MentalModel]:
        """Update an existing model."""
        model = self.models.get(model_id)
        if not model:
            return None
        
        if name is not None:
            model.name = name
        if description is not None:
            model.description = description
        if steps is not None:
            model.steps = steps
        if heuristics is not None:
            model.heuristics = heuristics
        
        model.updated_at = datetime.now(timezone.utc)
        self._save_index()
        return model
    
    def delete_model(self, model_id: str) -> bool:
        """Delete a model from the registry."""
        if model_id not in self.models:
            return False
        
        del self.models[model_id]
        self._save_index()
        logger.info(f"Deleted model {model_id}")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        type_counts = {}
        for model in self.models.values():
            type_counts[model.model_type.value] = type_counts.get(model.model_type.value, 0) + 1
        
        total_usage = sum(m.usage_count for m in self.models.values())
        avg_success = sum(m.success_rate for m in self.models.values()) / len(self.models) if self.models else 0.0
        
        return {
            "total_models": len(self.models),
            "total_usage": total_usage,
            "by_type": type_counts,
            "average_success_rate": avg_success,
            "usage_records": len(self.usage_history),
        }
