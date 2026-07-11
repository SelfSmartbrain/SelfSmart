'''problem_generator.py

Extracts real problems from system data for self‑play training.
Queries actual system issues, failures, and anomalies instead of synthetic data.
''' 

import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.db.models import FailureIncident, Execution, Task

logger = get_logger(__name__)


class ProblemGenerator:
    """
    Extracts real problems from system data for self-play training.
    
    Sources of real problems:
    1. Failure incidents from the database
    2. Failed executions with error messages
    3. Tasks with high failure rates
    4. Performance anomalies (slow executions)
    5. User-reported issues (if available)
    """
    
    def __init__(self):
        settings = get_settings()
        llm_kwargs = {
            "model": settings.anthropic_model,
            "api_key": settings.anthropic_api_key.get_secret_value(),
            "temperature": 0.3,
            "max_tokens": 2048,
        }
        if settings.anthropic_base_url:
            llm_kwargs["base_url"] = settings.anthropic_base_url
        self.llm = ChatAnthropic(**llm_kwargs)
        self.logger = logger

    async def generate(
        self, 
        db: AsyncSession,
        source: str = "auto",
        limit: int = 10
    ) -> Dict[str, str]:
        """
        Extract a real problem from system data.
        
        Args:
            db: Database session
            source: Problem source - "failures", "errors", "performance", "auto"
            limit: Number of recent records to consider
            
        Returns:
            Dict with problem description and metadata
        """
        self.logger.info(f"Generating problem from source: {source}")
        
        if source == "auto":
            # Auto-select the best available source
            problem = await self._select_best_problem(db, limit)
        elif source == "failures":
            problem = await self._extract_from_failures(db, limit)
        elif source == "errors":
            problem = await self._extract_from_errors(db, limit)
        elif source == "performance":
            problem = await self._extract_from_performance(db, limit)
        else:
            self.logger.warning(f"Unknown source {source}, falling back to failures")
            problem = await self._extract_from_failures(db, limit)
        
        return problem

    async def _select_best_problem(self, db: AsyncSession, limit: int) -> Dict[str, str]:
        """Select the best available problem from all sources."""
        # Try failures first (most critical)
        try:
            problem = await self._extract_from_failures(db, limit)
            if problem and problem.get("description"):
                return problem
        except Exception as e:
            self.logger.warning(f"Failed to extract from failures: {e}")
        
        # Try errors next
        try:
            problem = await self._extract_from_errors(db, limit)
            if problem and problem.get("description"):
                return problem
        except Exception as e:
            self.logger.warning(f"Failed to extract from errors: {e}")
        
        # Try performance issues
        try:
            problem = await self._extract_from_performance(db, limit)
            if problem and problem.get("description"):
                return problem
        except Exception as e:
            self.logger.warning(f"Failed to extract from performance: {e}")
        
        # Fallback to a generic problem if no real data available
        return {
            "description": "Improve system reliability by addressing common failure patterns in autonomous task execution.",
            "source": "fallback",
            "priority": "medium"
        }

    async def _extract_from_failures(self, db: AsyncSession, limit: int) -> Dict[str, str]:
        """Extract problems from failure incidents."""
        # Query recent unresolved failures
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        query = select(FailureIncident).where(
            and_(
                FailureIncident.created_at >= cutoff,
                FailureIncident.status.in_(["open", "recovering"])
            )
        ).order_by(desc(FailureIncident.created_at)).limit(limit)
        
        result = await db.execute(query)
        failures = result.scalars().all()
        
        if not failures:
            return {
                "description": "No recent failure incidents found. System is operating normally.",
                "source": "failures",
                "priority": "low"
            }
        
        # Select a random failure from recent ones
        failure = random.choice(failures)
        
        # Use LLM to formulate a clear problem description
        problem_desc = await self._formulate_problem_from_failure(failure)
        
        return {
            "description": problem_desc,
            "source": "failures",
            "incident_id": str(failure.id),
            "priority": failure.priority,
            "failure_type": failure.failure_type
        }

    async def _extract_from_errors(self, db: AsyncSession, limit: int) -> Dict[str, str]:
        """Extract problems from failed executions."""
        # Query recent failed executions
        cutoff = datetime.utcnow() - timedelta(days=3)
        
        query = select(Execution).where(
            and_(
                Execution.created_at >= cutoff,
                Execution.status == "failed",
                Execution.error.isnot(None)
            )
        ).order_by(desc(Execution.created_at)).limit(limit)
        
        result = await db.execute(query)
        executions = result.scalars().all()
        
        if not executions:
            return {
                "description": "No recent execution errors found.",
                "source": "errors",
                "priority": "low"
            }
        
        # Select a random failed execution
        execution = random.choice(executions)
        
        # Use LLM to formulate a problem description
        problem_desc = await self._formulate_problem_from_execution(execution)
        
        return {
            "description": problem_desc,
            "source": "errors",
            "execution_id": str(execution.id),
            "agent_id": execution.agent_id,
            "priority": "high"
        }

    async def _extract_from_performance(self, db: AsyncSession, limit: int) -> Dict[str, str]:
        """Extract problems from performance anomalies (slow executions)."""
        # Query executions that took longer than expected
        cutoff = datetime.utcnow() - timedelta(days=1)
        
        # Assume > 60 seconds is slow for this example
        query = select(Execution).where(
            and_(
                Execution.created_at >= cutoff,
                Execution.status == "completed",
                Execution.end_time.isnot(None),
                (Execution.end_time - Execution.created_at) > timedelta(seconds=60)
            )
        ).order_by(desc(Execution.created_at)).limit(limit)
        
        result = await db.execute(query)
        executions = result.scalars().all()
        
        if not executions:
            return {
                "description": "No recent performance anomalies detected.",
                "source": "performance",
                "priority": "low"
            }
        
        # Select a random slow execution
        execution = random.choice(executions)
        duration = (execution.end_time - execution.created_at).total_seconds()
        
        problem_desc = await self._formulate_problem_from_performance(execution, duration)
        
        return {
            "description": problem_desc,
            "source": "performance",
            "execution_id": str(execution.id),
            "duration_seconds": duration,
            "priority": "medium"
        }

    async def _formulate_problem_from_failure(self, failure: FailureIncident) -> str:
        """Use LLM to formulate a clear problem description from a failure incident."""
        system_prompt = """You are a system reliability engineer. Given a failure incident, formulate a clear, actionable problem description that an autonomous agent could work to solve.

Focus on:
- The core issue
- Impact on the system
- What needs to be fixed or improved

Keep the description concise (1-2 sentences) and actionable."""

        user_prompt = f"""Formulate a problem description from this failure incident:

Type: {failure.failure_type}
Description: {failure.description or 'No description provided'}
Context: {failure.context or 'No context provided'}
Status: {failure.status}
Priority: {failure.priority}

Provide a clear, actionable problem description."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            self.logger.error(f"Failed to formulate problem from failure: {e}")
            return f"Resolve {failure.failure_type} failure: {failure.description or 'Unknown issue'}"

    async def _formulate_problem_from_execution(self, execution: Execution) -> str:
        """Use LLM to formulate a problem description from a failed execution."""
        system_prompt = """You are a system reliability engineer. Given a failed execution, formulate a clear, actionable problem description.

Focus on:
- The error that occurred
- What the execution was trying to do
- How to prevent similar failures

Keep the description concise (1-2 sentences) and actionable."""

        user_prompt = f"""Formulate a problem description from this failed execution:

Agent ID: {execution.agent_id}
Task: {execution.task or 'Unknown task'}
Error: {execution.error or 'Unknown error'}
Status: {execution.status}

Provide a clear, actionable problem description."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            self.logger.error(f"Failed to formulate problem from execution: {e}")
            return f"Fix execution failure: {execution.error or 'Unknown error'} in task {execution.task or 'unknown'}"

    async def _formulate_problem_from_performance(self, execution: Execution, duration: float) -> str:
        """Use LLM to formulate a problem description from a slow execution."""
        system_prompt = """You are a performance engineer. Given a slow execution, formulate a clear, actionable problem description.

Focus on:
- What took too long
- Potential optimization opportunities
- How to improve performance

Keep the description concise (1-2 sentences) and actionable."""

        user_prompt = f"""Formulate a problem description from this slow execution:

Agent ID: {execution.agent_id}
Task: {execution.task or 'Unknown task'}
Duration: {duration:.2f} seconds
Status: {execution.status}

Provide a clear, actionable problem description for performance optimization."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            self.logger.error(f"Failed to formulate problem from performance: {e}")
            return f"Optimize performance for task {execution.task or 'unknown'} which took {duration:.2f} seconds"

    def __repr__(self):
        return "ProblemGenerator(real_data=True)"
