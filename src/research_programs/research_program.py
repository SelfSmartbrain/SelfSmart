"""
Research Program - Long-running autonomous research

The ResearchProgram is responsible for:
- Defining research programs
- Managing research lifecycle
- Tracking research progress
- Generating research insights
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class ProgramStatus(Enum):
    """Status of a research program"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class ResearchHypothesis:
    """A research hypothesis"""
    hypothesis_id: str
    statement: str
    confidence: float  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)
    status: str = "proposed"  # proposed, testing, confirmed, refuted
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class ResearchExperiment:
    """A research experiment"""
    experiment_id: str
    description: str
    hypothesis_id: str
    status: str = "pending"  # pending, running, completed, failed
    results: Optional[Dict[str, Any]] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class ResearchProgram:
    """A long-running research program"""
    program_id: str
    title: str
    description: str
    domain: str
    status: ProgramStatus = ProgramStatus.DRAFT
    hypotheses: List[ResearchHypothesis] = field(default_factory=list)
    experiments: List[ResearchExperiment] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress(self) -> float:
        """Calculate research progress"""
        if not self.hypotheses:
            return 0.0
        
        confirmed = sum(1 for h in self.hypotheses if h.status == "confirmed")
        refuted = sum(1 for h in self.hypotheses if h.status == "refuted")
        
        return (confirmed + refuted) / len(self.hypotheses)
    
    def add_hypothesis(self, statement: str, confidence: float = 0.5) -> ResearchHypothesis:
        """Add a hypothesis to the program"""
        hypothesis = ResearchHypothesis(
            hypothesis_id=f"{self.program_id}_hyp_{len(self.hypotheses)}",
            statement=statement,
            confidence=confidence,
        )
        self.hypotheses.append(hypothesis)
        return hypothesis
    
    def add_experiment(self, description: str, hypothesis_id: str) -> ResearchExperiment:
        """Add an experiment to the program"""
        experiment = ResearchExperiment(
            experiment_id=f"{self.program_id}_exp_{len(self.experiments)}",
            description=description,
            hypothesis_id=hypothesis_id,
        )
        self.experiments.append(experiment)
        return experiment
