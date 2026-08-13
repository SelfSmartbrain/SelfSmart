"""
Auto Fine-Tune Trigger - Connects evaluator feedback to fine-tuning pipeline.

This module monitors evaluation results and automatically triggers fine-tuning
when requirements fail, enabling the system to learn from its mistakes.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.llm.local_weight_engine import LocalWeightEngine
from src.learning.requirement_finetune_pipeline import (
    RequirementFineTunePipeline,
    FineTuneConfig,
    TrainingExample,
    create_training_examples_from_feedback,
)
from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AutoFineTuneConfig:
    """Configuration for automatic fine-tuning trigger"""
    evaluation_threshold: float = 0.8  # Trigger fine-tuning if score < threshold
    max_auto_finetune_epochs: int = 3
    auto_finetune_learning_rate: float = 2e-4
    adapter_save_path: str = "data/adapters/requirement_adapter"
    require_safety_approval: bool = True
    max_concurrent_finetunes: int = 1


@dataclass
class FineTuneTriggerRecord:
    """Record of a fine-tuning trigger event"""
    trigger_id: str
    requirement_id: str
    evaluation_score: float
    trigger_timestamp: datetime
    fine_tune_config: FineTuneConfig
    training_examples_count: int
    fine_tune_results: Optional[Dict[str, Any]] = None
    adapter_reloaded: bool = False
    status: str = "triggered"  # triggered, training, completed, failed


class AutoFineTuneTrigger:
    """
    Monitors evaluator feedback and automatically triggers fine-tuning
    when requirements fail to meet quality thresholds.
    """
    
    def __init__(
        self,
        engine: LocalWeightEngine,
        pipeline: RequirementFineTunePipeline,
        config: Optional[AutoFineTuneConfig] = None,
    ):
        self.engine = engine
        self.pipeline = pipeline
        self.config = config or AutoFineTuneConfig()
        self._trigger_history: List[FineTuneTriggerRecord] = []
        self._active_finetunes: int = 0
        
    def check_evaluation_score(self, eval_result: Dict[str, Any]) -> bool:
        """
        Check if evaluation score triggers auto fine-tuning.
        
        Args:
            eval_result: Evaluation result from evaluator agent
            
        Returns:
            True if fine-tuning should be triggered
        """
        score = eval_result.get("score", 1.0)
        passes = eval_result.get("passes", True)
        
        # Trigger if score is below threshold or explicitly fails
        should_trigger = score < self.config.evaluation_threshold or not passes
        
        if should_trigger:
            logger.info(
                f"Auto fine-tune triggered: score={score:.3f}, "
                f"threshold={self.config.evaluation_threshold}, passes={passes}"
            )
        
        return should_trigger
    
    def trigger_fine_tune(
        self,
        requirement_id: str,
        eval_result: Dict[str, Any],
        failed_requirement: str,
        expected_behavior: str,
        actual_output: str,
    ) -> FineTuneTriggerRecord:
        """
        Trigger automatic fine-tuning based on failed evaluation.
        
        Args:
            requirement_id: Unique identifier for the failed requirement
            eval_result: Full evaluation result from evaluator
            failed_requirement: The requirement that failed
            expected_behavior: What the correct behavior should be
            actual_output: What the model actually produced
            
        Returns:
            FineTuneTriggerRecord with trigger details and results
        """
        if self._active_finetunes >= self.config.max_concurrent_finetunes:
            logger.warning("Max concurrent fine-tunes reached, skipping trigger")
            return FineTuneTriggerRecord(
                trigger_id=str(uuid.uuid4()),
                requirement_id=requirement_id,
                evaluation_score=eval_result.get("score", 0.0),
                trigger_timestamp=datetime.now(),
                fine_tune_config=FineTuneConfig(),
                training_examples_count=0,
                status="skipped_max_concurrent",
            )
        
        # Create training examples from the feedback
        training_examples = create_training_examples_from_feedback(
            failed_requirement=failed_requirement,
            expected_behavior=expected_behavior,
            actual_output=actual_output,
            requirement_id=requirement_id,
        )
        
        # Configure fine-tuning
        fine_tune_config = FineTuneConfig(
            epochs=self.config.max_auto_finetune_epochs,
            learning_rate=self.config.auto_finetune_learning_rate,
            output_dir=self.config.adapter_save_path,
        )
        
        # Create trigger record
        trigger_id = str(uuid.uuid4())
        record = FineTuneTriggerRecord(
            trigger_id=trigger_id,
            requirement_id=requirement_id,
            evaluation_score=eval_result.get("score", 0.0),
            trigger_timestamp=datetime.now(),
            fine_tune_config=fine_tune_config,
            training_examples_count=len(training_examples),
        )
        
        self._trigger_history.append(record)
        self._active_finetunes += 1
        
        logger.info(f"Starting auto fine-tune {trigger_id} for requirement {requirement_id}")
        
        try:
            record.status = "training"
            
            # Run fine-tuning
            results = self.pipeline.fine_tune(
                training_examples=training_examples,
                epochs=fine_tune_config.epochs,
                learning_rate=fine_tune_config.learning_rate,
            )
            
            record.fine_tune_results = results
            record.status = "completed"
            
            # Save adapter
            adapter_path = self.pipeline.save_adapter(fine_tune_config.output_dir)
            logger.info(f"Adapter saved to {adapter_path}")
            
            # Reload adapter into engine for immediate use
            self.reload_adapter(adapter_path)
            record.adapter_reloaded = True
            
            logger.info(
                f"Auto fine-tune {trigger_id} completed: "
                f"final_loss={results['final_loss']:.4f}, "
                f"loss_decreased={results['loss_decreased']}"
            )
            
        except Exception as exc:
            logger.error(f"Auto fine-tune {trigger_id} failed: {exc}")
            record.status = "failed"
            record.fine_tune_results = {"error": str(exc)}
            
        finally:
            self._active_finetunes -= 1
        
        return record
    
    def reload_adapter(self, adapter_path: str) -> None:
        """
        Reload the updated adapter into the engine.
        
        Args:
            adapter_path: Path to the saved adapter
        """
        logger.info(f"Reloading adapter from {adapter_path}")
        self.engine.load_lora_adapter(adapter_path)
        logger.info("Adapter reloaded successfully - subsequent generations will use updated weights")
    
    def get_trigger_history(self) -> List[FineTuneTriggerRecord]:
        """Get history of all fine-tune triggers"""
        return self._trigger_history
    
    def get_latest_trigger(self) -> Optional[FineTuneTriggerRecord]:
        """Get the most recent trigger record"""
        if not self._trigger_history:
            return None
        return self._trigger_history[-1]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about auto fine-tune triggers"""
        total = len(self._trigger_history)
        completed = sum(1 for r in self._trigger_history if r.status == "completed")
        failed = sum(1 for r in self._trigger_history if r.status == "failed")
        skipped = sum(1 for r in self._trigger_history if r.status == "skipped_max_concurrent")
        
        loss_decreased_count = sum(
            1 for r in self._trigger_history 
            if r.fine_tune_results and r.fine_tune_results.get("loss_decreased", False)
        )
        
        return {
            "total_triggers": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": completed / total if total > 0 else 0.0,
            "loss_decreased_rate": loss_decreased_count / completed if completed > 0 else 0.0,
            "active_finetunes": self._active_finetunes,
        }


def create_auto_finetune_trigger(
    engine: LocalWeightEngine,
    config: Optional[AutoFineTuneConfig] = None,
) -> AutoFineTuneTrigger:
    """
    Factory function to create an AutoFineTuneTrigger with all dependencies.
    
    Args:
        engine: LocalWeightEngine instance
        config: Optional AutoFineTuneConfig
        
    Returns:
        Configured AutoFineTuneTrigger instance
    """
    pipeline = RequirementFineTunePipeline(engine, FineTuneConfig())
    return AutoFineTuneTrigger(engine, pipeline, config)