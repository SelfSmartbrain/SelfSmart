"""
Program Memory - Memory for research programs

The ProgramMemory is responsible for:
- Storing research program data
- Managing research insights
- Tracking program history
- Knowledge accumulation
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json


logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of program memory"""

    HYPOTHESIS = "hypothesis"
    EXPERIMENT = "experiment"
    INSIGHT = "insight"
    RESULT = "result"
    REFERENCE = "reference"


@dataclass
class ProgramMemoryEntry:
    """A memory entry for a research program"""

    entry_id: str
    program_id: str
    memory_type: MemoryType
    content: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5


class ProgramMemory:
    """
    Memory system for research programs.

    Provides:
    - Research data storage
    - Insight tracking
    - History management
    - Knowledge retrieval
    """

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries

        # Memory storage
        self._memory: Dict[str, ProgramMemoryEntry] = {}
        self._program_memory: Dict[str, Set[str]] = defaultdict(set)
        self._type_index: Dict[MemoryType, Set[str]] = defaultdict(set)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)

        # Statistics
        self._entries_added = 0
        self._entries_retrieved = 0

    async def initialize(self) -> None:
        """Initialize program memory"""
        logger.info("ProgramMemory initialized")

    async def add_entry(
        self,
        program_id: str,
        memory_type: MemoryType,
        content: str,
        data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
    ) -> ProgramMemoryEntry:
        """
        Add a memory entry.

        Args:
            program_id: Program identifier
            memory_type: Type of memory
            content: Content string
            data: Additional data
            tags: Tags for indexing
            importance: Importance score

        Returns:
            Memory entry
        """
        entry_id = f"{program_id}_{memory_type.value}_{datetime.now().timestamp()}"

        entry = ProgramMemoryEntry(
            entry_id=entry_id,
            program_id=program_id,
            memory_type=memory_type,
            content=content,
            data=data or {},
            tags=tags or [],
            importance=importance,
        )

        self._memory[entry_id] = entry
        self._program_memory[program_id].add(entry_id)
        self._type_index[memory_type].add(entry_id)

        for tag in entry.tags:
            self._tag_index[tag].add(entry_id)

        self._entries_added += 1

        # Check max entries
        if len(self._memory) > self.max_entries:
            await self._cleanup_old_entries()

        logger.debug(f"Added memory entry {entry_id} for program {program_id}")
        return entry

    async def get_entry(self, entry_id: str) -> Optional[ProgramMemoryEntry]:
        """Get a memory entry by ID"""
        self._entries_retrieved += 1
        return self._memory.get(entry_id)

    async def get_program_memory(
        self,
        program_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
    ) -> List[ProgramMemoryEntry]:
        """
        Get memory entries for a program.

        Args:
            program_id: Program identifier
            memory_type: Filter by memory type
            limit: Maximum entries to return

        Returns:
            List of memory entries
        """
        entry_ids = self._program_memory.get(program_id, set())

        if memory_type:
            type_ids = self._type_index.get(memory_type, set())
            entry_ids = entry_ids.intersection(type_ids)

        entries = [self._memory[eid] for eid in entry_ids if eid in self._memory]

        # Sort by importance and timestamp
        entries.sort(key=lambda e: (e.importance, e.timestamp), reverse=True)

        return entries[:limit]

    async def search_by_tag(
        self,
        tag: str,
        program_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ProgramMemoryEntry]:
        """
        Search memory entries by tag.

        Args:
            tag: Tag to search for
            program_id: Filter by program (optional)
            limit: Maximum entries to return

        Returns:
            List of memory entries
        """
        entry_ids = self._tag_index.get(tag, set())

        if program_id:
            program_ids = self._program_memory.get(program_id, set())
            entry_ids = entry_ids.intersection(program_ids)

        entries = [self._memory[eid] for eid in entry_ids if eid in self._memory]

        return entries[:limit]

    async def search_by_content(
        self,
        query: str,
        program_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ProgramMemoryEntry]:
        """
        Search memory entries by content.

        Args:
            query: Search query
            program_id: Filter by program (optional)
            limit: Maximum entries to return

        Returns:
            List of memory entries
        """
        query_lower = query.lower()

        entries = []
        for entry in self._memory.values():
            if program_id and entry.program_id != program_id:
                continue

            if query_lower in entry.content.lower():
                entries.append(entry)

        # Sort by importance
        entries.sort(key=lambda e: e.importance, reverse=True)

        return entries[:limit]

    async def get_insights(
        self,
        program_id: str,
        min_importance: float = 0.5,
    ) -> List[ProgramMemoryEntry]:
        """
        Get insights for a program.

        Args:
            program_id: Program identifier
            min_importance: Minimum importance threshold

        Returns:
            List of insight entries
        """
        entries = await self.get_program_memory(
            program_id,
            MemoryType.INSIGHT,
        )

        return [e for e in entries if e.importance >= min_importance]

    async def add_insight(
        self,
        program_id: str,
        insight: str,
        importance: float = 0.7,
        tags: Optional[List[str]] = None,
    ) -> ProgramMemoryEntry:
        """
        Add an insight to program memory.

        Args:
            program_id: Program identifier
            insight: Insight content
            importance: Importance score
            tags: Tags for indexing

        Returns:
            Memory entry
        """
        return await self.add_entry(
            program_id=program_id,
            memory_type=MemoryType.INSIGHT,
            content=insight,
            importance=importance,
            tags=tags or ["insight"],
        )

    async def _cleanup_old_entries(self) -> int:
        """Clean up old entries when exceeding max"""
        # Remove oldest entries with low importance
        entries = list(self._memory.values())
        entries.sort(key=lambda e: (e.importance, e.timestamp))

        to_remove = entries[: len(entries) - self.max_entries]

        for entry in to_remove:
            await self._remove_entry(entry.entry_id)

        return len(to_remove)

    async def _remove_entry(self, entry_id: str) -> None:
        """Remove a memory entry"""
        if entry_id not in self._memory:
            return

        entry = self._memory[entry_id]

        # Remove from indexes
        self._program_memory[entry.program_id].discard(entry_id)
        self._type_index[entry.memory_type].discard(entry_id)

        for tag in entry.tags:
            self._tag_index[tag].discard(entry_id)

        del self._memory[entry_id]

    def get_metrics(self) -> Dict[str, Any]:
        """Get memory metrics"""
        return {
            "entries_added": self._entries_added,
            "entries_retrieved": self._entries_retrieved,
            "total_entries": len(self._memory),
            "programs_tracked": len(self._program_memory),
            "average_importance": (
                sum(e.importance for e in self._memory.values()) / len(self._memory)
                if self._memory
                else 0.0
            ),
        }
