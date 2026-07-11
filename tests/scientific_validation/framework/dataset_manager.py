"""
Dataset management for scientific validation experiments.
"""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import random
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatasetItem:
    """A single item in a validation dataset."""
    
    item_id: str
    category: str
    difficulty: str  # easy, medium, hard
    
    # Task data
    task_data: Dict[str, Any]
    
    # Ground truth for evaluation
    ground_truth: Any
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "item_id": self.item_id,
            "category": self.category,
            "difficulty": self.difficulty,
            "task_data": self.task_data,
            "ground_truth": self.ground_truth,
            "metadata": self.metadata,
        }


class DatasetGenerator(ABC):
    """Abstract base class for dataset generators."""
    
    @abstractmethod
    def generate(self, num_items: int, seed: int) -> List[DatasetItem]:
        """Generate dataset items."""
        pass
    
    @abstractmethod
    def get_category(self) -> str:
        """Get dataset category."""
        pass


class DatasetManager:
    """Manage validation datasets with caching and reproducibility."""
    
    def __init__(self, data_dir: Path, cache_enabled: bool = True):
        self.data_dir = data_dir
        self.cache_enabled = cache_enabled
        self.datasets_dir = data_dir / "datasets"
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        
        self.generators: Dict[str, DatasetGenerator] = {}
    
    def register_generator(self, generator: DatasetGenerator) -> None:
        """Register a dataset generator."""
        category = generator.get_category()
        self.generators[category] = generator
        logger.info(f"Registered dataset generator for category: {category}")
    
    def get_or_generate_dataset(
        self,
        category: str,
        num_items: int,
        seed: int,
        force_regenerate: bool = False,
    ) -> List[DatasetItem]:
        """Get dataset from cache or generate new."""
        if category not in self.generators:
            raise ValueError(f"No generator registered for category: {category}")
        
        # Check cache
        cache_path = self._get_cache_path(category, num_items, seed)
        if self.cache_enabled and cache_path.exists() and not force_regenerate:
            logger.info(f"Loading cached dataset from {cache_path}")
            return self._load_dataset(cache_path)
        
        # Generate new dataset
        logger.info(f"Generating dataset for category {category} with {num_items} items")
        generator = self.generators[category]
        items = generator.generate(num_items, seed)
        
        # Cache if enabled
        if self.cache_enabled:
            self._save_dataset(items, cache_path)
        
        return items
    
    def _get_cache_path(self, category: str, num_items: int, seed: int) -> Path:
        """Get cache path for dataset."""
        filename = f"{category}_{num_items}_seed_{seed}.pkl"
        return self.datasets_dir / filename
    
    def _save_dataset(self, items: List[DatasetItem], path: Path) -> None:
        """Save dataset to cache."""
        with open(path, "wb") as f:
            pickle.dump(items, f)
        logger.debug(f"Saved dataset to {path}")
    
    def _load_dataset(self, path: Path) -> List[DatasetItem]:
        """Load dataset from cache."""
        with open(path, "rb") as f:
            return pickle.load(f)
    
    def list_cached_datasets(self) -> List[Dict[str, Any]]:
        """List all cached datasets."""
        datasets = []
        
        for path in self.datasets_dir.glob("*.pkl"):
            # Parse filename: category_num_items_seed_seed.pkl
            parts = path.stem.split("_")
            if len(parts) >= 4:
                category = "_".join(parts[:-3])
                num_items = int(parts[-3])
                seed = int(parts[-1])
                
                datasets.append({
                    "category": category,
                    "num_items": num_items,
                    "seed": seed,
                    "path": str(path),
                })
        
        return datasets
    
    def clear_cache(self, category: Optional[str] = None) -> None:
        """Clear cached datasets."""
        if category:
            # Clear specific category
            for path in self.datasets_dir.glob(f"{category}_*.pkl"):
                path.unlink()
                logger.info(f"Cleared cache: {path}")
        else:
            # Clear all
            for path in self.datasets_dir.glob("*.pkl"):
                path.unlink()
            logger.info("Cleared all dataset cache")
    
    def export_dataset_json(
        self,
        category: str,
        num_items: int,
        seed: int,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Export dataset to JSON."""
        items = self.get_or_generate_dataset(category, num_items, seed)
        
        if output_path is None:
            output_path = self.data_dir / f"{category}_{num_items}_seed_{seed}.json"
        
        with open(output_path, "w") as f:
            json.dump([item.to_dict() for item in items], f, indent=2)
        
        logger.info(f"Exported dataset to {output_path}")
        return output_path
