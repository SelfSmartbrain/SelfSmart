"""mental_models.py

Defines reusable mental models for various cognitive tasks.
Provides structured approaches to problem-solving and decision-making.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ModelType(str, Enum):
    """Types of mental models."""
    OPTIMIZATION = "optimization"
    SCHEDULING = "scheduling"
    RESEARCH = "research"
    LEARNING = "learning"
    PLANNING = "planning"
    DECISION = "decision"
    PROBLEM_SOLVING = "problem_solving"
    PREDICTION = "prediction"


@dataclass
class MentalModel:
    """A reusable mental model for cognitive tasks."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    model_type: ModelType = ModelType.PROBLEM_SOLVING
    domain: str = ""
    steps: List[str] = field(default_factory=list)
    heuristics: List[str] = field(default_factory=list)
    success_rate: float = 0.5
    usage_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "model_type": self.model_type.value,
            "domain": self.domain,
            "steps": self.steps,
            "heuristics": self.heuristics,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PrebuiltModels:
    """Collection of prebuilt mental models."""
    
    @staticmethod
    def pareto_optimization() -> MentalModel:
        """Pareto Principle (80/20 Rule) for optimization."""
        return MentalModel(
            name="Pareto Optimization",
            description="Apply 80/20 rule: 80% of results come from 20% of efforts",
            model_type=ModelType.OPTIMIZATION,
            domain="productivity",
            steps=[
                "Identify all tasks/activities",
                "Measure impact of each task",
                "Rank by impact-to-effort ratio",
                "Focus on top 20% high-impact tasks",
                "Delegate or eliminate low-impact tasks",
            ],
            heuristics=[
                "If a task takes >20% of time but contributes <20% of value, reconsider",
                "Always ask: What's the 20% that drives 80% of results?",
            ],
            success_rate=0.75,
            metadata={"origin": "Vilfredo Pareto"},
        )
    
    @staticmethod
    def first_things_first() -> MentalModel:
        """Eisenhower Matrix for prioritization."""
        return MentalModel(
            name="First Things First",
            description="Prioritize by urgency and importance using Eisenhower Matrix",
            model_type=ModelType.PLANNING,
            domain="productivity",
            steps=[
                "List all tasks",
                "Categorize by urgency (urgent/not urgent)",
                "Categorize by importance (important/not important)",
                "Do: Important + Urgent",
                "Schedule: Important + Not Urgent",
                "Delegate: Urgent + Not Important",
                "Eliminate: Not Important + Not Urgent",
            ],
            heuristics=[
                "Important but not urgent = strategic work",
                "Urgent but not important = distraction",
            ],
            success_rate=0.80,
            metadata={"origin": "Dwight Eisenhower"},
        )
    
    @staticmethod
    def scientific_method() -> MentalModel:
        """Scientific method for research."""
        return MentalModel(
            name="Scientific Method",
            description="Systematic approach to investigation and discovery",
            model_type=ModelType.RESEARCH,
            domain="science",
            steps=[
                "Observe phenomenon",
                "Formulate hypothesis",
                "Design experiment",
                "Collect data",
                "Analyze results",
                "Draw conclusions",
                "Peer review and replication",
            ],
            heuristics=[
                "Null hypothesis should be falsifiable",
                "Control variables to isolate effects",
                "Sample size must be statistically significant",
            ],
            success_rate=0.90,
            metadata={"origin": "Francis Bacon"},
        )
    
    @staticmethod
    def spaced_repetition() -> MentalModel:
        """Spaced repetition for learning."""
        return MentalModel(
            name="Spaced Repetition",
            description="Optimize learning by reviewing at increasing intervals",
            model_type=ModelType.LEARNING,
            domain="education",
            steps=[
                "Learn new material",
                "Review after 1 day",
                "Review after 3 days",
                "Review after 1 week",
                "Review after 2 weeks",
                "Review after 1 month",
                "Review after 3 months",
            ],
            heuristics=[
                "Review just before forgetting point",
                "Active recall is better than passive review",
                "Interleave related topics",
            ],
            success_rate=0.85,
            metadata={"origin": "Hermann Ebbinghaus"},
        )
    
    @staticmethod
    def critical_path() -> MentalModel:
        """Critical Path Method for scheduling."""
        return MentalModel(
            name="Critical Path Method",
            description="Identify longest path of dependent tasks to determine project duration",
            model_type=ModelType.SCHEDULING,
            domain="project_management",
            steps=[
                "List all tasks",
                "Identify dependencies",
                "Estimate duration for each task",
                "Draw network diagram",
                "Calculate earliest start/finish times",
                "Calculate latest start/finish times",
                "Identify critical path (zero slack)",
                "Monitor critical path closely",
            ],
            heuristics=[
                "Critical path determines minimum project duration",
                "Non-critical tasks have slack/flexibility",
                "Resource leveling can affect critical path",
            ],
            success_rate=0.78,
            metadata={"origin": "DuPont Corporation"},
        )
    
    @staticmethod
    def first_principles() -> MentalModel:
        """First principles thinking for problem-solving."""
        return MentalModel(
            name="First Principles Thinking",
            description="Break down problems to fundamental truths and build up from there",
            model_type=ModelType.PROBLEM_SOLVING,
            domain="general",
            steps=[
                "Identify the problem",
                "Break down to fundamental assumptions",
                "Question each assumption",
                "Rebuild solution from first principles",
                "Test and iterate",
            ],
            heuristics=[
                "Distinguish between analogy and first principles",
                "Physics > reasoning by analogy",
                "What would you do if you started from scratch?",
            ],
            success_rate=0.82,
            metadata={"origin": "Aristotle"},
        )
    
    @staticmethod
    def bayesian_inference() -> MentalModel:
        """Bayesian inference for prediction."""
        return MentalModel(
            name="Bayesian Inference",
            description="Update probabilities as new evidence arrives",
            model_type=ModelType.PREDICTION,
            domain="statistics",
            steps=[
                "Start with prior probability",
                "Gather new evidence",
                "Calculate likelihood of evidence under hypothesis",
                "Update to posterior probability",
                "Repeat as new evidence arrives",
            ],
            heuristics=[
                "Prior beliefs matter but should be updatable",
                "Strong evidence can overcome weak priors",
                "Consider base rates",
            ],
            success_rate=0.88,
            metadata={"origin": "Thomas Bayes"},
        )
    
    @staticmethod
    def inversion() -> MentalModel:
        """Inversion for decision-making."""
        return MentalModel(
            name="Inversion",
            description="Think backwards: avoid stupidity rather than seeking brilliance",
            model_type=ModelType.DECISION,
            domain="general",
            steps=[
                "Define goal",
                "Ask: What would guarantee failure?",
                "List all ways to fail",
                "Avoid those failure modes",
                "Proceed with confidence",
            ],
            heuristics=[
                "It's easier to avoid stupidity than be brilliant",
                "Tell me where I'm going to die so I don't go there",
                "Negation is often easier than affirmation",
            ],
            success_rate=0.76,
            metadata={"origin": "Charlie Munger"},
        )
    
    @staticmethod
    def divide_and_conquer() -> MentalModel:
        """Divide and conquer for problem-solving."""
        return MentalModel(
            name="Divide and Conquer",
            description="Break complex problems into smaller, manageable sub-problems",
            model_type=ModelType.PROBLEM_SOLVING,
            domain="algorithms",
            steps=[
                "Identify the complex problem",
                "Divide into smaller sub-problems",
                "Solve each sub-problem independently",
                "Combine sub-solutions",
                "Verify overall solution",
            ],
            heuristics=[
                "Sub-problems should be independent",
                "Recursion is often useful",
                "Parallelize when possible",
            ],
            success_rate=0.84,
            metadata={"origin": "Julius Caesar"},
        )
    
    @staticmethod
    def get_all_prebuilt() -> List[MentalModel]:
        """Get all prebuilt mental models."""
        return [
            PrebuiltModels.pareto_optimization(),
            PrebuiltModels.first_things_first(),
            PrebuiltModels.scientific_method(),
            PrebuiltModels.spaced_repetition(),
            PrebuiltModels.critical_path(),
            PrebuiltModels.first_principles(),
            PrebuiltModels.bayesian_inference(),
            PrebuiltModels.inversion(),
            PrebuiltModels.divide_and_conquer(),
        ]
