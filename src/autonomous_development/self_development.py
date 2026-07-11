"""
Self Development - Self-analysis and improvement capabilities

The SelfDevelopment module is responsible for:
- Analyzing own codebase
- Identifying improvement opportunities
- Generating self-improvement plans
- Safety controls for self-modification
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import os


logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety levels for self-modification"""
    SAFE = "safe"  # Read-only analysis
    MODERATE = "moderate"  # Suggestions only
    RISKY = "risky"  # Automated changes with review
    DANGEROUS = "dangerous"  # Full automation (disabled by default)


@dataclass
class AnalysisResult:
    """Result of self-analysis"""
    analysis_id: str
    component: str
    findings: List[str]
    suggestions: List[str]
    risk_level: SafetyLevel
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImprovementPlan:
    """Plan for self-improvement"""
    plan_id: str
    title: str
    description: str
    changes: List[Dict[str, Any]]
    safety_level: SafetyLevel
    estimated_impact: str
    requires_approval: bool = True
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


class SelfDevelopment:
    """
    Self-development capabilities with safety controls.
    
    Provides:
    - Codebase analysis
    - Improvement identification
    - Safe self-modification
    - Strict safety controls
    """
    
    def __init__(
        self,
        repo_path: str = "/Users/subh/Documents/ModelX",
        max_safety_level: SafetyLevel = SafetyLevel.MODERATE,
    ):
        self.repo_path = repo_path
        self.max_safety_level = max_safety_level
        
        # Analysis history
        self._analysis_history: List[AnalysisResult] = []
        self._improvement_plans: List[ImprovementPlan] = []
        
        # Safety controls
        self._approved_changes: Set[str] = set()
        self._blocked_patterns: List[str] = [
            "rm -rf",
            "delete all",
            "drop database",
            "format disk",
        ]
        
        # Statistics
        self._analyses_performed = 0
        self._improvements_suggested = 0
    
    async def initialize(self) -> None:
        """Initialize self-development"""
        logger.info(f"SelfDevelopment initialized (max safety: {self.max_safety_level.value})")
    
    async def analyze_component(
        self,
        component: str,
        analysis_type: str = "general",
    ) -> AnalysisResult:
        """
        Analyze a component of the codebase.
        
        Args:
            component: Component to analyze (e.g., "cognitive_kernel")
            analysis_type: Type of analysis
            
        Returns:
            Analysis result
        """
        analysis_id = f"analysis_{datetime.now().timestamp()}"
        
        # Placeholder for component analysis
        # In full implementation, would:
        # - Parse code
        # - Identify patterns
        # - Check for issues
        # - Generate suggestions
        
        findings = [
            f"Analyzed {component}",
            "Code structure is well-organized",
            "Consider adding more documentation",
        ]
        
        suggestions = [
            "Add type hints to functions",
            "Improve error handling",
            "Add unit tests",
        ]
        
        result = AnalysisResult(
            analysis_id=analysis_id,
            component=component,
            findings=findings,
            suggestions=suggestions,
            risk_level=SafetyLevel.SAFE,
            metadata={"analysis_type": analysis_type},
        )
        
        self._analysis_history.append(result)
        self._analyses_performed += 1
        
        logger.info(f"Analyzed component {component}")
        return result
    
    async def analyze_entire_codebase(self) -> List[AnalysisResult]:
        """
        Analyze the entire codebase.
        
        Returns:
            List of analysis results
        """
        components = [
            "cognitive_kernel",
            "memory",
            "reasoning",
            "agent_society",
            "identity",
            "research_programs",
        ]
        
        results = []
        for component in components:
            result = await self.analyze_component(component)
            results.append(result)
        
        return results
    
    async def generate_improvement_plan(
        self,
        analysis_results: List[AnalysisResult],
        safety_level: SafetyLevel = SafetyLevel.MODERATE,
    ) -> ImprovementPlan:
        """
        Generate an improvement plan from analysis results.
        
        Args:
            analysis_results: Analysis results to base plan on
            safety_level: Desired safety level
            
        Returns:
            Improvement plan
        """
        # Enforce max safety level
        if safety_level.value > self.max_safety_level.value:
            safety_level = self.max_safety_level
        
        plan_id = f"plan_{datetime.now().timestamp()}"
        
        # Aggregate suggestions
        all_suggestions = []
        for result in analysis_results:
            all_suggestions.extend(result.suggestions)
        
        # Create change proposals
        changes = []
        for i, suggestion in enumerate(all_suggestions[:5]):  # Limit to 5 changes
            changes.append({
                "change_id": f"change_{i}",
                "description": suggestion,
                "risk": SafetyLevel.SAFE.value,
                "files_affected": [],
            })
        
        plan = ImprovementPlan(
            plan_id=plan_id,
            title="Codebase Improvement Plan",
            description="Automated improvement plan based on analysis",
            changes=changes,
            safety_level=safety_level,
            estimated_impact="moderate",
            requires_approval=safety_level != SafetyLevel.SAFE,
        )
        
        self._improvement_plans.append(plan)
        self._improvements_suggested += 1
        
        logger.info(f"Generated improvement plan {plan_id}")
        return plan
    
    async def check_safety(self, change: Dict[str, Any]) -> bool:
        """
        Check if a change is safe to apply.
        
        Args:
            change: Change to check
            
        Returns:
            True if change is safe
        """
        description = change.get("description", "").lower()
        
        # Check for blocked patterns
        for pattern in self._blocked_patterns:
            if pattern in description:
                logger.warning(f"Blocked unsafe change containing: {pattern}")
                return False
        
        # Check safety level
        risk = change.get("risk", SafetyLevel.SAFE.value)
        if SafetyLevel(risk).value > self.max_safety_level.value:
            logger.warning(f"Change exceeds max safety level: {risk}")
            return False
        
        return True
    
    async def apply_improvement(
        self,
        plan_id: str,
        require_approval: bool = True,
    ) -> bool:
        """
        Apply an improvement plan.
        
        Args:
            plan_id: Plan identifier
            require_approval: Whether to require approval
            
        Returns:
            True if applied successfully
        """
        plan = next((p for p in self._improvement_plans if p.plan_id == plan_id), None)
        
        if not plan:
            logger.warning(f"Plan {plan_id} not found")
            return False
        
        # Check safety level
        if plan.safety_level.value > self.max_safety_level.value:
            logger.error(f"Plan exceeds max safety level")
            return False
        
        # Check approval requirement
        if plan.requires_approval and require_approval:
            logger.warning(f"Plan {plan_id} requires approval")
            return False
        
        # Check each change
        for change in plan.changes:
            if not await self.check_safety(change):
                logger.error(f"Change failed safety check")
                return False
        
        # Placeholder for applying changes
        # In full implementation, would:
        # - Create backup
        # - Apply changes
        # - Run tests
        # - Rollback if failed
        
        logger.info(f"Applied improvement plan {plan_id}")
        return True
    
    def get_analysis_history(self, limit: int = 50) -> List[AnalysisResult]:
        """Get analysis history"""
        return self._analysis_history[-limit:]
    
    def get_improvement_plans(self, status: Optional[str] = None) -> List[ImprovementPlan]:
        """Get improvement plans"""
        plans = self._improvement_plans
        
        if status:
            plans = [p for p in plans if p.metadata.get("status") == status]
        
        return plans
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get self-development metrics"""
        return {
            "analyses_performed": self._analyses_performed,
            "improvements_suggested": self._improvements_suggested,
            "analysis_history_size": len(self._analysis_history),
            "plans_created": len(self._improvement_plans),
            "max_safety_level": self.max_safety_level.value,
        }
