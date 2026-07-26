"""Scheduler for periodic knowledge fitness evaluation and pruning."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from src.config.logging import get_logger
from .fitness_engine import KnowledgeFitnessEngine, FitnessScore, DEFAULT_FITNESS_CONFIG
from .pruner import BeliefPruner, PruningConfig, PruneAction

logger = get_logger(__name__)


@dataclass
class SchedulerConfig:
    """Configuration for the fitness scheduler."""
    
    # Schedule
    evaluation_interval_hours: int = 24       # How often to run fitness evaluation
    pruning_interval_hours: int = 168         # How often to run pruning (weekly)
    validation_interval_hours: int = 72       # How often to validate beliefs
    
    # Windows
    maintenance_window_start: int = 2         # UTC hour to start maintenance (2 AM)
    maintenance_window_hours: int = 4         # Duration of maintenance window
    
    # Limits
    max_beliefs_per_evaluation: int = 5000    # Max beliefs to evaluate per run
    max_prune_per_run: int = 50               # Max beliefs to prune per run
    
    # Behavior
    auto_prune: bool = True                   # Automatically prune low-fitness beliefs
    auto_archive: bool = True                 # Automatically archive review candidates
    auto_validate: bool = True                # Automatically validate sample
    
    # Callbacks
    on_evaluation_complete: Optional[Callable[[List[FitnessScore]], Any]] = None
    on_pruning_complete: Optional[Callable[[List[Any]], Any]] = None
    on_error: Optional[Callable[[Exception], Any]] = None


class KnowledgeFitnessScheduler:
    """
    Schedules and runs periodic knowledge fitness evaluation and pruning.
    
    Runs during maintenance windows to minimize impact on active agents.
    """
    
    def __init__(
        self,
        fitness_engine: KnowledgeFitnessEngine,
        pruner: BeliefPruner,
        config: Optional[SchedulerConfig] = None,
    ):
        self.fitness_engine = fitness_engine
        self.pruner = pruner
        self.config = config or SchedulerConfig()
        
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._last_evaluation: Optional[datetime] = None
        self._last_pruning: Optional[datetime] = None
        self._last_validation: Optional[datetime] = None
        self._evaluation_count = 0
        self._pruning_count = 0
        self._validation_count = 0
        
        # Apply config limits to sub-components
        self.fitness_engine.config.max_prune_per_run = self.config.max_beliefs_per_evaluation
        self.pruner.config.max_prune_per_run = self.config.max_prune_per_run
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        logger.info("Starting KnowledgeFitnessScheduler")
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._evaluation_loop()),
            asyncio.create_task(self._pruning_loop()),
            asyncio.create_task(self._validation_loop()),
        ]
        
        logger.info("KnowledgeFitnessScheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks = []
        logger.info("KnowledgeFitnessScheduler stopped")
    
    def is_in_maintenance_window(self) -> bool:
        """Check if current time is in maintenance window."""
        now = datetime.utcnow()
        start_hour = self.config.maintenance_window_start
        end_hour = (start_hour + self.config.maintenance_window_hours) % 24
        
        current_hour = now.hour
        
        if start_hour <= end_hour:
            return start_hour <= current_hour < end_hour
        else:  # Window crosses midnight
            return current_hour >= start_hour or current_hour < end_hour
    
    async def _evaluation_loop(self) -> None:
        """Background loop for fitness evaluation."""
        while self._running:
            try:
                # Wait until next evaluation interval
                await self._wait_for_interval(
                    self.config.evaluation_interval_hours,
                    self._last_evaluation,
                )
                
                # Check maintenance window
                if not self.is_in_maintenance_window():
                    # Wait until window opens
                    await self._wait_for_maintenance_window()
                
                await self.run_evaluation()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in evaluation loop: {e}")
                if self.config.on_error:
                    await self.config.on_error(e)
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def _pruning_loop(self) -> None:
        """Background loop for pruning."""
        while self._running:
            try:
                # Wait until next pruning interval
                await self._wait_for_interval(
                    self.config.pruning_interval_hours,
                    self._last_pruning,
                )
                
                # Check maintenance window
                if not self.is_in_maintenance_window():
                    await self._wait_for_maintenance_window()
                
                if self.config.auto_prune:
                    await self.run_pruning()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pruning loop: {e}")
                if self.config.on_error:
                    await self.config.on_error(e)
                await asyncio.sleep(3600)
    
    async def _validation_loop(self) -> None:
        """Background loop for belief validation."""
        while self._running:
            try:
                # Wait until next validation interval
                await self._wait_for_interval(
                    self.config.validation_interval_hours,
                    self._last_validation,
                )
                
                # Check maintenance window
                if not self.is_in_maintenance_window():
                    await self._wait_for_maintenance_window()
                
                if self.config.auto_validate:
                    await self.run_validation()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in validation loop: {e}")
                if self.config.on_error:
                    await self.config.on_error(e)
                await asyncio.sleep(3600)
    
    async def _wait_for_interval(
        self,
        interval_hours: int,
        last_run: Optional[datetime],
    ) -> None:
        """Wait until the next scheduled interval."""
        if last_run is None:
            # First run - wait until next maintenance window
            return
        
        next_run = last_run + timedelta(hours=interval_hours)
        now = datetime.utcnow()
        
        if now < next_run:
            wait_seconds = (next_run - now).total_seconds()
            logger.debug(f"Waiting {wait_seconds:.0f}s until next scheduled run")
            await asyncio.sleep(wait_seconds)
    
    async def _wait_for_maintenance_window(self) -> None:
        """Wait until the next maintenance window opens."""
        while self._running and not self.is_in_maintenance_window():
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def run_evaluation(self) -> List[FitnessScore]:
        """Run a fitness evaluation cycle."""
        logger.info("Starting knowledge fitness evaluation")
        start_time = datetime.utcnow()
        
        try:
            scores = await self.fitness_engine.evaluate_all_beliefs()
            
            self._last_evaluation = datetime.utcnow()
            self._evaluation_count += 1
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Fitness evaluation complete in {elapsed:.1f}s: "
                f"{len(scores)} beliefs evaluated"
            )
            
            if self.config.on_evaluation_complete:
                await self.config.on_evaluation_complete(scores)
            
            return scores
            
        except Exception as e:
            logger.error(f"Fitness evaluation failed: {e}")
            if self.config.on_error:
                await self.config.on_error(e)
            raise
    
    async def run_pruning(self) -> List[Any]:
        """Run a pruning cycle based on latest fitness scores."""
        logger.info("Starting belief pruning")
        start_time = datetime.utcnow()
        
        try:
            # Get latest fitness scores
            scores = await self.fitness_engine.get_pruning_candidates(
                limit=self.config.max_prune_per_run
            )
            
            if not scores:
                logger.info("No pruning candidates found")
                return []
            
            # Execute pruning
            results = await self.pruner.prune_beliefs(scores)
            
            self._last_pruning = datetime.utcnow()
            self._pruning_count += 1
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            success_count = sum(1 for r in results if r.success)
            logger.info(
                f"Pruning complete in {elapsed:.1f}s: "
                f"{success_count}/{len(results)} successful"
            )
            
            if self.config.on_pruning_complete:
                await self.config.on_pruning_complete(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Pruning failed: {e}")
            if self.config.on_error:
                await self.config.on_error(e)
            raise
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run a validation cycle on a sample of beliefs."""
        logger.info("Starting belief validation")
        start_time = datetime.utcnow()
        
        try:
            # Get all scores
            scores = await self.fitness_engine.evaluate_all_beliefs()
            
            # Sample for validation
            import random
            sample_size = int(len(scores) * self.fitness_engine.config.validation_sample_rate)
            sample = random.sample(scores, min(sample_size, len(scores)))
            
            validation_results = {
                "validated": 0,
                "confirmed": 0,
                "contradicted": 0,
                "errors": 0,
            }
            
            for fs in sample:
                if fs.overall_fitness < self.fitness_engine.config.high_value_threshold:
                    # Validate this belief
                    result = await self._validate_belief(fs.belief_id)
                    validation_results["validated"] += 1
                    if result == "confirmed":
                        validation_results["confirmed"] += 1
                    elif result == "contradicted":
                        validation_results["contradicted"] += 1
                    else:
                        validation_results["errors"] += 1
            
            self._last_validation = datetime.utcnow()
            self._validation_count += 1
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Validation complete in {elapsed:.1f}s: "
                f"{validation_results}"
            )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            if self.config.on_error:
                await self.config.on_error(e)
            raise
    
    async def _validate_belief(self, belief_id: str) -> str:
        """Validate a single belief against current knowledge."""
        # Placeholder - in full implementation would:
        # 1. Retrieve the belief
        # 2. Check against current knowledge base
        # 3. Query external sources if needed
        # 4. Update validation_count or contradiction_count
        return "confirmed"
    
    async def run_full_maintenance(self) -> Dict[str, Any]:
        """Run complete maintenance cycle."""
        logger.info("Running full knowledge maintenance cycle")
        start_time = datetime.utcnow()
        
        results = {
            "evaluation": None,
            "pruning": None,
            "validation": None,
            "duration_seconds": 0,
        }
        
        try:
            # Evaluation
            results["evaluation"] = await self.run_evaluation()
            
            # Pruning
            if self.config.auto_prune:
                results["pruning"] = await self.run_pruning()
            
            # Validation
            if self.config.auto_validate:
                results["validation"] = await self.run_validation()
            
        except Exception as e:
            logger.error(f"Maintenance cycle failed: {e}")
            results["error"] = str(e)
        
        results["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Full maintenance cycle complete in {results['duration_seconds']:.1f}s")
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "running": self._running,
            "evaluation_count": self._evaluation_count,
            "pruning_count": self._pruning_count,
            "validation_count": self._validation_count,
            "last_evaluation": self._last_evaluation.isoformat() if self._last_evaluation else None,
            "last_pruning": self._last_pruning.isoformat() if self._last_pruning else None,
            "last_validation": self._last_validation.isoformat() if self._last_validation else None,
            "in_maintenance_window": self.is_in_maintenance_window(),
            "fitness_engine": self.fitness_engine.get_stats(),
            "pruner": self.pruner.get_stats(),
        }


class ManualFitnessController:
    """
    Manual controller for running fitness operations on demand.
    
    Useful for testing, debugging, or operator-triggered maintenance.
    """
    
    def __init__(
        self,
        fitness_engine: KnowledgeFitnessEngine,
        pruner: BeliefPruner,
    ):
        self.fitness_engine = fitness_engine
        self.pruner = pruner
    
    async def evaluate_collection(self, collection: str) -> List[FitnessScore]:
        """Evaluate fitness for a single Qdrant collection."""
        return await self.fitness_engine.evaluate_all_beliefs(collections=[collection])
    
    async def evaluate_label(self, label: str) -> List[FitnessScore]:
        """Evaluate fitness for a single Neo4j label."""
        return await self.fitness_engine.evaluate_all_beliefs(labels=[label])
    
    async def prune_by_threshold(
        self,
        threshold: float,
        dry_run: bool = True,
    ) -> List[Any]:
        """Prune all beliefs below threshold."""
        self.pruner.config.dry_run = dry_run
        
        scores = await self.fitness_engine.get_pruning_candidates(threshold=threshold)
        return await self.pruner.prune_beliefs(scores)
    
    async def force_revalidate(self, belief_ids: List[str]) -> Dict[str, str]:
        """Force revalidation of specific beliefs."""
        results = {}
        for bid in belief_ids:
            # Would call validation logic
            results[bid] = "pending"
        return results
    
    async def get_belief_details(self, belief_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific belief."""
        # Search in Qdrant
        if self.fitness_engine.qdrant_client:
            from src.rag.vector_store import MANAGED_COLLECTIONS
            for collection in MANAGED_COLLECTIONS:
                data = await self.fitness_engine.qdrant_client.get(collection, belief_id)
                if data:
                    return {"source": "qdrant", "collection": collection, "data": data}
        
        # Search in Neo4j
        if self.fitness_engine.neo4j_client:
            cypher = "MATCH (n {id: $id}) RETURN n"
            result = await self.fitness_engine.neo4j_client.execute_query(
                cypher, {"id": belief_id}
            )
            if result:
                return {"source": "neo4j", "data": dict(result[0]["n"])}
        
        return None