"""discovery_loop.py

Integrates World Model, Theory Engine, Experiment Engine, and Belief Engine
into a continuous scientific discovery loop.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class DiscoveryPhase(str, Enum):
    """Phases of the scientific discovery loop."""
    OBSERVATION = "observation"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    EXPERIMENT_DESIGN = "experiment_design"
    EXPERIMENT_EXECUTION = "experiment_execution"
    ANALYSIS = "analysis"
    THEORY_FORMATION = "theory_formation"
    BELIEF_UPDATE = "belief_update"
    PREDICTION = "prediction"


@dataclass
class DiscoveryIteration:
    """A single iteration of the discovery loop."""
    iteration_id: str
    phase: DiscoveryPhase
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    observations: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    experiments: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    theories: List[str] = field(default_factory=list)
    beliefs: List[Dict[str, Any]] = field(default_factory=list)
    predictions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration_id": self.iteration_id,
            "phase": self.phase.value,
            "timestamp": self.timestamp.isoformat(),
            "observation_count": len(self.observations),
            "hypothesis_count": len(self.hypotheses),
            "experiment_count": len(self.experiments),
            "theory_count": len(self.theories),
            "metadata": self.metadata,
        }


class DiscoveryLoop:
    """
    Continuous scientific discovery loop.
    
    Integrates:
    - World Model (observations, patterns)
    - Theory Engine (theory formation)
    - Experiment Engine (design and execution)
    - Belief Engine (belief updates)
    """
    
    def __init__(self):
        self.iterations: List[DiscoveryIteration] = []
        self.current_phase = DiscoveryPhase.OBSERVATION
        self.current_iteration: Optional[DiscoveryIteration] = None
        self.knowledge_base: Dict[str, Any] = {}
        
        # Component references (to be injected)
        self.world_model = None
        self.theory_engine = None
        self.experiment_engine = None
        self.belief_engine = None
        
        logger.info("DiscoveryLoop initialized")
    
    def set_components(
        self,
        world_model: Optional[Any] = None,
        theory_engine: Optional[Any] = None,
        experiment_engine: Optional[Any] = None,
        belief_engine: Optional[Any] = None,
    ) -> None:
        """Set the component engines."""
        self.world_model = world_model
        self.theory_engine = theory_engine
        self.experiment_engine = experiment_engine
        self.belief_engine = belief_engine
        logger.info("DiscoveryLoop components configured")
    
    def start_iteration(self) -> DiscoveryIteration:
        """Start a new discovery iteration."""
        iteration = DiscoveryIteration(
            iteration_id=str(uuid.uuid4()),
            phase=DiscoveryPhase.OBSERVATION,
        )
        
        self.iterations.append(iteration)
        self.current_iteration = iteration
        self.current_phase = DiscoveryPhase.OBSERVATION
        
        logger.info(f"Started discovery iteration {iteration.iteration_id}")
        return iteration
    
    async def observation_phase(self, observations: List[str]) -> None:
        """Process observations from the world model."""
        if not self.current_iteration:
            self.start_iteration()
        
        self.current_iteration.observations = observations
        self.current_phase = DiscoveryPhase.OBSERVATION
        
        # Store in knowledge base
        self.knowledge_base["observations"] = self.knowledge_base.get("observations", []) + observations
        
        logger.info(f"Observation phase: {len(observations)} observations")
    
    async def hypothesis_generation_phase(self) -> List[str]:
        """Generate hypotheses from observations."""
        if not self.current_iteration:
            return []
        
        self.current_phase = DiscoveryPhase.HYPOTHESIS_GENERATION
        
        hypotheses = []
        
        # Use world model to generate hypotheses if available
        if self.world_model and hasattr(self.world_model, "generate_hypotheses"):
            hypotheses = await self.world_model.generate_hypotheses(
                self.current_iteration.observations
            )
        else:
            # Simple hypothesis generation
            hypotheses = self._generate_simple_hypotheses(
                self.current_iteration.observations
            )
        
        self.current_iteration.hypotheses = hypotheses
        
        logger.info(f"Hypothesis generation phase: {len(hypotheses)} hypotheses")
        return hypotheses
    
    def _generate_simple_hypotheses(self, observations: List[str]) -> List[str]:
        """Generate simple hypotheses from observations."""
        hypotheses = []
        
        # Extract patterns
        if len(observations) > 1:
            hypotheses.append(f"Pattern: {observations[0][:50]}... recurs across observations")
        
        # Generate causal hypotheses
        if len(observations) > 2:
            hypotheses.append("Causal relationship exists between observed variables")
        
        # Generate correlation hypotheses
        hypotheses.append("Variables co-vary in observed data")
        
        return hypotheses
    
    async def experiment_design_phase(self) -> List[Dict[str, Any]]:
        """Design experiments to test hypotheses."""
        if not self.current_iteration:
            return []
        
        self.current_phase = DiscoveryPhase.EXPERIMENT_DESIGN
        
        experiments = []
        
        # Design experiments for each hypothesis
        for i, hypothesis in enumerate(self.current_iteration.hypotheses):
            experiment = {
                "experiment_id": f"exp_{uuid.uuid4()}",
                "hypothesis": hypothesis,
                "design": f"Test hypothesis {i+1}",
                "variables": ["independent", "dependent"],
                "method": "controlled_experiment",
            }
            experiments.append(experiment)
        
        self.current_iteration.experiments = experiments
        
        logger.info(f"Experiment design phase: {len(experiments)} experiments designed")
        return experiments
    
    async def experiment_execution_phase(self) -> List[Dict[str, Any]]:
        """Execute designed experiments."""
        if not self.current_iteration:
            return []
        
        self.current_phase = DiscoveryPhase.EXPERIMENT_EXECUTION
        
        results = []
        
        # Execute experiments
        for experiment in self.current_iteration.experiments:
            # Simulate execution
            result = {
                "experiment_id": experiment["experiment_id"],
                "outcome": "success" if hash(experiment["hypothesis"]) % 2 == 0 else "failure",
                "data": {"value": hash(experiment["hypothesis"]) % 100},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results.append(result)
        
        self.current_iteration.results = results
        
        logger.info(f"Experiment execution phase: {len(results)} experiments executed")
        return results
    
    async def analysis_phase(self) -> Dict[str, Any]:
        """Analyze experiment results."""
        if not self.current_iteration:
            return {}
        
        self.current_phase = DiscoveryPhase.ANALYSIS
        
        # Analyze results
        successful = sum(1 for r in self.current_iteration.results if r["outcome"] == "success")
        total = len(self.current_iteration.results)
        
        analysis = {
            "total_experiments": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
        }
        
        self.current_iteration.metadata["analysis"] = analysis
        
        logger.info(f"Analysis phase: success rate {analysis['success_rate']:.1%}")
        return analysis
    
    async def theory_formation_phase(self) -> List[str]:
        """Form theories from successful experiments."""
        if not self.current_iteration:
            return []
        
        self.current_phase = DiscoveryPhase.THEORY_FORMATION
        
        theories = []
        
        # Form theories from successful experiments
        successful_results = [
            r for r in self.current_iteration.results
            if r["outcome"] == "success"
        ]
        
        for result in successful_results:
            theory = f"Theory: {result['experiment_id']} demonstrates consistent pattern"
            theories.append(theory)
        
        self.current_iteration.theories = theories
        
        logger.info(f"Theory formation phase: {len(theories)} theories formed")
        return theories
    
    async def belief_update_phase(self) -> List[Dict[str, Any]]:
        """Update beliefs based on theories and evidence."""
        if not self.current_iteration:
            return []
        
        self.current_phase = DiscoveryPhase.BELIEF_UPDATE
        
        beliefs = []
        
        # Update beliefs for each theory
        for theory in self.current_iteration.theories:
            belief = {
                "theory": theory,
                "confidence": 0.7,  # Initial confidence
                "evidence": len(self.current_iteration.results),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            beliefs.append(belief)
        
        self.current_iteration.beliefs = beliefs
        
        logger.info(f"Belief update phase: {len(beliefs)} beliefs updated")
        return beliefs
    
    async def prediction_phase(self) -> List[str]:
        """Generate predictions based on updated beliefs."""
        if not self.current_iteration:
            return []
        
        self.current_phase = DiscoveryPhase.PREDICTION
        
        predictions = []
        
        # Generate predictions from beliefs
        for belief in self.current_iteration.beliefs:
            prediction = f"Prediction: {belief['theory']} implies future outcomes"
            predictions.append(prediction)
        
        self.current_iteration.predictions = predictions
        
        logger.info(f"Prediction phase: {len(predictions)} predictions generated")
        return predictions
    
    async def run_full_loop(
        self,
        observations: List[str],
    ) -> DiscoveryIteration:
        """Run the complete discovery loop."""
        iteration = self.start_iteration()
        
        # Run all phases
        await self.observation_phase(observations)
        await self.hypothesis_generation_phase()
        await self.experiment_design_phase()
        await self.experiment_execution_phase()
        await self.analysis_phase()
        await self.theory_formation_phase()
        await self.belief_update_phase()
        await self.prediction_phase()
        
        logger.info(f"Completed discovery loop iteration {iteration.iteration_id}")
        return iteration
    
    def get_iteration(self, iteration_id: str) -> Optional[DiscoveryIteration]:
        """Get an iteration by ID."""
        for iteration in self.iterations:
            if iteration.iteration_id == iteration_id:
                return iteration
        return None
    
    def get_latest_iteration(self) -> Optional[DiscoveryIteration]:
        """Get the latest iteration."""
        return self.iterations[-1] if self.iterations else None
    
    def get_iterations_by_phase(self, phase: DiscoveryPhase) -> List[DiscoveryIteration]:
        """Get iterations that ended in a specific phase."""
        return [i for i in self.iterations if i.phase == phase]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get discovery loop statistics."""
        phase_counts = {}
        for iteration in self.iterations:
            phase_counts[iteration.phase.value] = phase_counts.get(iteration.phase.value, 0) + 1
        
        total_observations = sum(len(i.observations) for i in self.iterations)
        total_hypotheses = sum(len(i.hypotheses) for i in self.iterations)
        total_experiments = sum(len(i.experiments) for i in self.iterations)
        total_theories = sum(len(i.theories) for i in self.iterations)
        
        return {
            "total_iterations": len(self.iterations),
            "by_phase": phase_counts,
            "total_observations": total_observations,
            "total_hypotheses": total_hypotheses,
            "total_experiments": total_experiments,
            "total_theories": total_theories,
            "hypotheses_per_iteration": total_hypotheses / len(self.iterations) if self.iterations else 0.0,
            "theories_per_iteration": total_theories / len(self.iterations) if self.iterations else 0.0,
        }
