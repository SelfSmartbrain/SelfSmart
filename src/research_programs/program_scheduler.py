"""
Program Scheduler - Schedules and executes research programs

The ProgramScheduler is responsible for:
- Scheduling research program execution
- Managing program lifecycles
- Coordinating autonomous research
- Resource allocation for programs
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class SchedulePriority(Enum):
    """Priority levels for program scheduling"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class ScheduledProgram:
    """A scheduled research program"""
    program_id: str
    priority: SchedulePriority
    frequency: str  # "once", "daily", "weekly", "continuous"
    next_run: float
    last_run: Optional[float] = None
    interval_hours: float = 24.0
    max_duration: float = 3600.0  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProgramScheduler:
    """
    Scheduler for research programs.
    
    Provides:
    - Program scheduling
    - Execution coordination
    - Resource management
    - Lifecycle tracking
    """
    
    def __init__(self):
        self._scheduled_programs: Dict[str, ScheduledProgram] = {}
        self._running_programs: Set[str] = set()
        
        # Execution statistics
        self._executions_started = 0
        self._executions_completed = 0
        self._executions_failed = 0
        
        # Scheduler state
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize the program scheduler"""
        self._running = True
        asyncio.create_task(self._scheduler_loop())
        logger.info("ProgramScheduler initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the scheduler"""
        self._running = False
        logger.info("ProgramScheduler shutdown complete")
    
    async def schedule_program(
        self,
        program_id: str,
        priority: SchedulePriority = SchedulePriority.MEDIUM,
        frequency: str = "once",
        interval_hours: float = 24.0,
        start_delay: float = 0.0,
    ) -> bool:
        """
        Schedule a research program.
        
        Args:
            program_id: Program identifier
            priority: Schedule priority
            frequency: Execution frequency
            interval_hours: Interval between runs (for recurring)
            start_delay: Delay before first run
            
        Returns:
            True if scheduled successfully
        """
        next_run = datetime.now().timestamp() + start_delay
        
        scheduled = ScheduledProgram(
            program_id=program_id,
            priority=priority,
            frequency=frequency,
            next_run=next_run,
            interval_hours=interval_hours,
        )
        
        self._scheduled_programs[program_id] = scheduled
        
        logger.info(
            f"Scheduled program {program_id} ({frequency}, "
            f"priority: {priority.name})"
        )
        return True
    
    async def unschedule_program(self, program_id: str) -> bool:
        """
        Unschedule a program.
        
        Args:
            program_id: Program identifier
            
        Returns:
            True if unscheduled successfully
        """
        if program_id in self._scheduled_programs:
            del self._scheduled_programs[program_id]
            logger.info(f"Unscheduled program {program_id}")
            return True
        return False
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop"""
        while self._running:
            try:
                now = datetime.now().timestamp()
                
                # Check for programs ready to run
                for program_id, scheduled in self._scheduled_programs.items():
                    if now >= scheduled.next_run and program_id not in self._running_programs:
                        await self._execute_program(program_id, scheduled)
                
                await asyncio.sleep(1.0)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5.0)
    
    async def _execute_program(
        self,
        program_id: str,
        scheduled: ScheduledProgram,
    ) -> None:
        """Execute a scheduled program"""
        self._running_programs.add(program_id)
        scheduled.last_run = datetime.now().timestamp()
        self._executions_started += 1
        
        logger.info(f"Starting execution of program {program_id}")
        
        try:
            # Placeholder for program execution
            # In full implementation, would delegate to program executor
            await asyncio.sleep(min(1.0, scheduled.max_duration / 10.0))
            
            self._executions_completed += 1
            logger.info(f"Completed execution of program {program_id}")
            
        except Exception as e:
            self._executions_failed += 1
            logger.error(f"Execution failed for program {program_id}: {e}")
        
        finally:
            self._running_programs.discard(program_id)
            
            # Schedule next run if recurring
            if scheduled.frequency != "once":
                scheduled.next_run = datetime.now().timestamp() + (scheduled.interval_hours * 3600)
    
    async def trigger_program(self, program_id: str) -> bool:
        """
        Trigger immediate execution of a program.
        
        Args:
            program_id: Program identifier
            
        Returns:
            True if triggered successfully
        """
        if program_id not in self._scheduled_programs:
            logger.warning(f"Program {program_id} not scheduled")
            return False
        
        scheduled = self._scheduled_programs[program_id]
        scheduled.next_run = datetime.now().timestamp()
        
        logger.info(f"Triggered immediate execution of program {program_id}")
        return True
    
    def get_scheduled_programs(self) -> List[ScheduledProgram]:
        """Get all scheduled programs"""
        return list(self._scheduled_programs.values())
    
    def get_running_programs(self) -> Set[str]:
        """Get currently running programs"""
        return self._running_programs.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get scheduler metrics"""
        return {
            "executions_started": self._executions_started,
            "executions_completed": self._executions_completed,
            "executions_failed": self._executions_failed,
            "scheduled_programs": len(self._scheduled_programs),
            "running_programs": len(self._running_programs),
            "success_rate": (
                self._executions_completed / self._executions_started
                if self._executions_started > 0 else 0.0
            ),
        }
