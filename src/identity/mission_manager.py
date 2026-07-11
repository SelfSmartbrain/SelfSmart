"""
Mission Manager - Manages long-term missions and goals

The MissionManager is responsible for:
- Defining and tracking missions
 Managing long-term goals
- Monitoring mission progress
- Mission completion and archival
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class MissionStatus(Enum):
    """Status of a mission"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class GoalStatus(Enum):
    """Status of a goal"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Goal:
    """A goal within a mission"""
    goal_id: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 5
    progress: float = 0.0  # 0.0 to 1.0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Mission:
    """A long-term mission"""
    mission_id: str
    title: str
    description: str
    status: MissionStatus = MissionStatus.DRAFT
    goals: List[Goal] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    deadline: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress(self) -> float:
        """Calculate overall mission progress"""
        if not self.goals:
            return 0.0
        return sum(g.progress for g in self.goals) / len(self.goals)
    
    @property
    def is_overdue(self) -> bool:
        """Check if mission is overdue"""
        if self.deadline is None:
            return False
        return datetime.now().timestamp() > self.deadline


class MissionManager:
    """
    Manager for long-term missions and goals.
    
    Provides:
    - Mission creation and tracking
    - Goal management
    - Progress monitoring
    - Mission lifecycle management
    """
    
    def __init__(self):
        self._missions: Dict[str, Mission] = {}
        self._active_mission: Optional[str] = None
        
        # Statistics
        self._missions_created = 0
        self._missions_completed = 0
        self._goals_completed = 0
    
    async def initialize(self) -> None:
        """Initialize the mission manager"""
        logger.info("MissionManager initialized")
    
    async def create_mission(
        self,
        title: str,
        description: str,
        goals: Optional[List[Dict[str, Any]]] = None,
        deadline: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Mission:
        """
        Create a new mission.
        
        Args:
            title: Mission title
            description: Mission description
            goals: Initial goals
            deadline: Optional deadline
            metadata: Additional metadata
            
        Returns:
            Created mission
        """
        mission_id = f"mission_{datetime.now().timestamp()}"
        
        # Convert goal dicts to objects
        goal_objects = []
        if goals:
            for i, goal_dict in enumerate(goals):
                goal = Goal(
                    goal_id=f"{mission_id}_goal_{i}",
                    description=goal_dict["description"],
                    priority=goal_dict.get("priority", 5),
                    metadata=goal_dict.get("metadata", {}),
                )
                goal_objects.append(goal)
        
        mission = Mission(
            mission_id=mission_id,
            title=title,
            description=description,
            goals=goal_objects,
            deadline=deadline,
            metadata=metadata or {},
        )
        
        self._missions[mission_id] = mission
        self._missions_created += 1
        
        logger.info(f"Created mission {mission_id}: {title} with {len(goal_objects)} goals")
        return mission
    
    async def start_mission(self, mission_id: str) -> bool:
        """
        Start a mission.
        
        Args:
            mission_id: Mission identifier
            
        Returns:
            True if started successfully
        """
        if mission_id not in self._missions:
            logger.warning(f"Mission {mission_id} not found")
            return False
        
        mission = self._missions[mission_id]
        mission.status = MissionStatus.ACTIVE
        mission.started_at = datetime.now().timestamp()
        
        # Set as active mission
        self._active_mission = mission_id
        
        logger.info(f"Started mission {mission_id}")
        return True
    
    async def pause_mission(self, mission_id: str) -> bool:
        """
        Pause a mission.
        
        Args:
            mission_id: Mission identifier
            
        Returns:
            True if paused successfully
        """
        if mission_id not in self._missions:
            logger.warning(f"Mission {mission_id} not found")
            return False
        
        mission = self._missions[mission_id]
        mission.status = MissionStatus.PAUSED
        
        if self._active_mission == mission_id:
            self._active_mission = None
        
        logger.info(f"Paused mission {mission_id}")
        return True
    
    async def complete_mission(
        self,
        mission_id: str,
        results: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Complete a mission.
        
        Args:
            mission_id: Mission identifier
            results: Mission results
            
        Returns:
            True if completed successfully
        """
        if mission_id not in self._missions:
            logger.warning(f"Mission {mission_id} not found")
            return False
        
        mission = self._missions[mission_id]
        mission.status = MissionStatus.COMPLETED
        mission.completed_at = datetime.now().timestamp()
        mission.metadata["results"] = results or {}
        
        if self._active_mission == mission_id:
            self._active_mission = None
        
        self._missions_completed += 1
        
        logger.info(f"Completed mission {mission_id}")
        return True
    
    async def add_goal(
        self,
        mission_id: str,
        description: str,
        priority: int = 5,
    ) -> bool:
        """
        Add a goal to a mission.
        
        Args:
            mission_id: Mission identifier
            description: Goal description
            priority: Goal priority
            
        Returns:
            True if added successfully
        """
        if mission_id not in self._missions:
            logger.warning(f"Mission {mission_id} not found")
            return False
        
        mission = self._missions[mission_id]
        
        goal = Goal(
            goal_id=f"{mission_id}_goal_{len(mission.goals)}",
            description=description,
            priority=priority,
        )
        
        mission.goals.append(goal)
        
        logger.debug(f"Added goal to mission {mission_id}")
        return True
    
    async def update_goal_progress(
        self,
        goal_id: str,
        progress: float,
    ) -> bool:
        """
        Update goal progress.
        
        Args:
            goal_id: Goal identifier
            progress: Progress (0.0 to 1.0)
            
        Returns:
            True if updated successfully
        """
        # Find goal across all missions
        for mission in self._missions.values():
            for goal in mission.goals:
                if goal.goal_id == goal_id:
                    goal.progress = min(1.0, max(0.0, progress))
                    
                    if goal.progress >= 1.0 and goal.status != GoalStatus.COMPLETED:
                        goal.status = GoalStatus.COMPLETED
                        goal.completed_at = datetime.now().timestamp()
                        self._goals_completed += 1
                    
                    logger.debug(f"Updated goal {goal_id} progress to {progress:.2f}")
                    return True
        
        logger.warning(f"Goal {goal_id} not found")
        return False
    
    async def complete_goal(
        self,
        goal_id: str,
        results: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark a goal as completed.
        
        Args:
            goal_id: Goal identifier
            results: Goal results
            
        Returns:
            True if completed successfully
        """
        success = await self.update_goal_progress(goal_id, 1.0)
        
        if success:
            # Add results to goal
            for mission in self._missions.values():
                for goal in mission.goals:
                    if goal.goal_id == goal_id:
                        goal.metadata["results"] = results or {}
                        break
        
        return success
    
    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get a mission by ID"""
        return self._missions.get(mission_id)
    
    def get_active_mission(self) -> Optional[Mission]:
        """Get the currently active mission"""
        if self._active_mission:
            return self._missions.get(self._active_mission)
        return None
    
    def get_all_missions(
        self,
        status: Optional[MissionStatus] = None,
    ) -> List[Mission]:
        """Get all missions, optionally filtered by status"""
        missions = list(self._missions.values())
        
        if status:
            missions = [m for m in missions if m.status == status]
        
        return missions
    
    def get_overdue_missions(self) -> List[Mission]:
        """Get all overdue missions"""
        return [m for m in self._missions.values() if m.is_overdue]
    
    def get_mission_goals(
        self,
        mission_id: str,
        status: Optional[GoalStatus] = None,
    ) -> List[Goal]:
        """Get goals for a mission"""
        mission = self._missions.get(mission_id)
        
        if not mission:
            return []
        
        goals = mission.goals
        
        if status:
            goals = [g for g in goals if g.status == status]
        
        return goals
    
    async def check_mission_completion(self, mission_id: str) -> bool:
        """
        Check if a mission is complete.
        
        Args:
            mission_id: Mission identifier
            
        Returns:
            True if mission is complete
        """
        mission = self._missions.get(mission_id)
        
        if not mission:
            return False
        
        # Check if all goals are completed
        all_completed = all(g.status == GoalStatus.COMPLETED for g in mission.goals)
        
        if all_completed and mission.status == MissionStatus.ACTIVE:
            await self.complete_mission(mission_id)
        
        return all_completed
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get mission manager metrics"""
        return {
            "missions_created": self._missions_created,
            "missions_completed": self._missions_completed,
            "goals_completed": self._goals_completed,
            "active_missions": len(self.get_all_missions(MissionStatus.ACTIVE)),
            "overdue_missions": len(self.get_overdue_missions()),
            "total_goals": sum(len(m.goals) for m in self._missions.values()),
        }
