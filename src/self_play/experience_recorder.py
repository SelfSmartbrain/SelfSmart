"""
Experience Recorder - Records and manages learning experiences.

Provides structured storage, indexing, and querying of self-play
and agent experiences for continuous learning.
"""

import asyncio
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Awaitable

logger = logging.getLogger(__name__)


class ExperienceType(Enum):
    """Types of experiences."""
    SELF_PLAY = "self_play"
    AGENT_TASK = "agent_task"
    HUMAN_FEEDBACK = "human_feedback"
    AUTOMATED_TEST = "automated_test"
    EXPLORATION = "exploration"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"


@dataclass
class ExecutionTrace:
    """Detailed execution trace."""
    trace_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Code
    code: str = ""
    language: str = "python"
    stdin: str = ""
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    
    # Resources
    peak_memory_mb: float = 0.0
    cpu_time_seconds: float = 0.0
    
    # Steps
    steps: List[Dict[str, Any]] = field(default_factory=list)
    
    # Errors
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data


@dataclass
class RecorderTestResult:
    """Individual test result for recording."""
    test_id: str
    name: str
    passed: bool
    input_data: Any
    expected_output: Any
    actual_output: Any
    duration_ms: float
    error_message: Optional[str] = None
    points_earned: float = 0.0
    points_possible: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestSuiteResult:
    """Aggregated test suite results."""
    suite_id: str
    test_results: List[RecorderTestResult] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    total_duration_ms: float = 0.0
    all_passed: bool = False
    
    def __post_init__(self):
        self.total_tests = len(self.test_results)
        self.passed_tests = sum(1 for r in self.test_results if r.passed)
        self.failed_tests = sum(1 for r in self.test_results if not r.passed and r.error_message is None)
        self.error_tests = sum(1 for r in self.test_results if r.error_message is not None)
        self.total_duration_ms = sum(r.duration_ms for r in self.test_results)
        self.all_passed = self.passed_tests == self.total_tests and self.total_tests > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "test_results": [r.to_dict() for r in self.test_results],
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "error_tests": self.error_tests,
            "total_duration_ms": self.total_duration_ms,
            "all_passed": self.all_passed,
        }


@dataclass
class ExperienceRecord:
    """Complete experience record."""
    experience_id: str
    experience_type: ExperienceType
    timestamp: datetime
    
    # Problem context
    problem_id: str
    problem_description: str
    problem_domain: str
    problem_difficulty: int
    problem_skills: List[str] = field(default_factory=list)
    
    # Solution
    solution_code: str
    solution_language: str = "python"
    
    # Execution
    execution_trace: Optional[ExecutionTrace] = None
    test_results: Optional[TestSuiteResult] = None
    
    # Outcome
    success: bool = False
    score: float = 0.0
    
    # Learning signals
    skill_scores: Dict[str, float] = field(default_factory=dict)
    error_patterns: List[str] = field(default_factory=list)
    optimization_opportunities: List[str] = field(default_factory=list)
    
    # Metadata
    agent_version: str = "1.0"
    environment: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["experience_type"] = self.experience_type.value
        if self.execution_trace:
            data["execution_trace"] = self.execution_trace.to_dict()
        if self.test_results:
            data["test_results"] = self.test_results.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperienceRecord":
        """Create from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["experience_type"] = ExperienceType(data["experience_type"])
        if data.get("execution_trace"):
            et = data["execution_trace"]
            et["started_at"] = datetime.fromisoformat(et["started_at"])
            if et.get("completed_at"):
                et["completed_at"] = datetime.fromisoformat(et["completed_at"])
            data["execution_trace"] = ExecutionTrace(**et)
        if data.get("test_results"):
            tr = data["test_results"]
            tr["test_results"] = [RecorderTestResult(**r) for r in tr["test_results"]]
            data["test_results"] = TestSuiteResult(**tr)
        return cls(**data)


class ExperienceRecorder:
    """
    Records and manages learning experiences.
    
    Features:
    - SQLite storage with full-text search
    - In-memory buffering with periodic flush
    - Multiple output formats
    - Streaming callbacks
    - Query and analysis API
    """
    
    def __init__(
        self,
        storage_path: str = "./data/experiences",
        max_buffer_size: int = 1000,
        auto_flush: bool = True,
        flush_interval: float = 30.0,
        retention_days: int = 90,
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.max_buffer_size = max_buffer_size
        self.auto_flush = auto_flush
        self.flush_interval = flush_interval
        self.retention_days = retention_days
        
        # Buffer
        self._buffer: List[ExperienceRecord] = []
        self._buffer_lock = asyncio.Lock()
        
        # Database
        self._db_path = self.storage_path / "experiences.db"
        self._init_database()
        
        # Stats
        self._total_recorded = 0
        self._total_flushed = 0
        self._flush_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_recorded: List[Callable[[ExperienceRecord], Awaitable[None]]] = []
        self._on_flushed: List[Callable[[List[ExperienceRecord]], Awaitable[None]]] = []
    
    def _init_database(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    experience_id TEXT PRIMARY KEY,
                    experience_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    problem_id TEXT NOT NULL,
                    problem_description TEXT,
                    problem_domain TEXT,
                    problem_difficulty INTEGER,
                    problem_skills TEXT,
                    solution_code TEXT,
                    solution_language TEXT,
                    success BOOLEAN,
                    score REAL,
                    skill_scores TEXT,
                    error_patterns TEXT,
                    optimization_opportunities TEXT,
                    agent_version TEXT,
                    environment TEXT,
                    tags TEXT,
                    execution_trace TEXT,
                    test_results TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON experiences(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_problem_id ON experiences(problem_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_experience_type ON experiences(experience_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_success ON experiences(success)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_score ON experiences(score)
            """)
            conn.commit()
    
    async def start(self):
        """Start the recorder."""
        if self.auto_flush:
            self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info(f"ExperienceRecorder started: {self.storage_path}")
    
    async def stop(self):
        """Stop and flush."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        logger.info("ExperienceRecorder stopped")
    
    async def record(
        self,
        experience_type: ExperienceType,
        problem_id: str,
        problem_description: str,
        problem_domain: str,
        problem_difficulty: int,
        solution_code: str,
        execution_trace: Optional[ExecutionTrace] = None,
        test_results: Optional[TestSuiteResult] = None,
        success: bool = False,
        score: float = 0.0,
        problem_skills: Optional[List[str]] = None,
        skill_scores: Optional[Dict[str, float]] = None,
        error_patterns: Optional[List[str]] = None,
        optimization_opportunities: Optional[List[str]] = None,
        agent_version: str = "1.0",
        environment: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        solution_language: str = "python",
    ) -> ExperienceRecord:
        """Record an experience."""
        
        record = ExperienceRecord(
            experience_id=f"exp_{uuid.uuid4().hex[:12]}",
            experience_type=experience_type,
            timestamp=datetime.utcnow(),
            problem_id=problem_id,
            problem_description=problem_description,
            problem_domain=problem_domain,
            problem_difficulty=problem_difficulty,
            problem_skills=problem_skills or [],
            solution_code=solution_code,
            solution_language=solution_language,
            execution_trace=execution_trace,
            test_results=test_results,
            success=success,
            score=score,
            skill_scores=skill_scores or {},
            error_patterns=error_patterns or [],
            optimization_opportunities=optimization_opportunities or [],
            agent_version=agent_version,
            environment=environment or {},
            tags=tags or [],
        )
        
        # Add to buffer
        async with self._buffer_lock:
            self._buffer.append(record)
            self._total_recorded += 1
            
            # Auto-flush if buffer full
            if len(self._buffer) >= self.max_buffer_size:
                await self._flush_buffer()
        
        # Callbacks
        for callback in self._on_recorded:
            try:
                await callback(record)
            except Exception as e:
                logger.error(f"Record callback failed: {e}")
        
        return record
    
    async def _periodic_flush(self):
        """Periodic flush task."""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()
    
    async def flush(self):
        """Flush buffer to storage."""
        await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Flush buffer to database."""
        async with self._buffer_lock:
            if not self._buffer:
                return
            
            records = self._buffer[:]
            self._buffer.clear()
        
        try:
            with sqlite3.connect(self._db_path) as conn:
                for record in records:
                    conn.execute("""
                        INSERT INTO experiences VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """, (
                        record.experience_id,
                        record.experience_type.value,
                        record.timestamp.isoformat(),
                        record.problem_id,
                        record.problem_description,
                        record.problem_domain,
                        record.problem_difficulty,
                        json.dumps(record.problem_skills),
                        record.solution_code,
                        record.solution_language,
                        record.success,
                        record.score,
                        json.dumps(record.skill_scores),
                        json.dumps(record.error_patterns),
                        json.dumps(record.optimization_opportunities),
                        record.agent_version,
                        json.dumps(record.environment),
                        json.dumps(record.tags),
                        json.dumps(record.execution_trace.to_dict()) if record.execution_trace else None,
                        json.dumps(record.test_results.to_dict()) if record.test_results else None,
                    ))
                conn.commit()
            
            self._total_flushed += len(records)
            
            # Callbacks
            for callback in self._on_flushed:
                try:
                    await callback(records)
                except Exception as e:
                    logger.error(f"Flush callback failed: {e}")
            
            logger.debug(f"Flushed {len(records)} experiences")
            
        except Exception as e:
            logger.error(f"Flush failed: {e}")
            # Re-add to buffer on failure
            async with self._buffer_lock:
                self._buffer = records + self._buffer
    
    # Query methods
    
    async def query(
        self,
        experience_type: Optional[ExperienceType] = None,
        problem_id: Optional[str] = None,
        success: Optional[bool] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ExperienceRecord]:
        """Query experiences."""
        query = "SELECT * FROM experiences WHERE 1=1"
        params = []
        
        if experience_type:
            query += " AND experience_type = ?"
            params.append(experience_type.value)
        
        if problem_id:
            query += " AND problem_id = ?"
            params.append(problem_id)
        
        if success is not None:
            query += " AND success = ?"
            params.append(success)
        
        if min_score is not None:
            query += " AND score >= ?"
            params.append(min_score)
        
        if max_score is not None:
            query += " AND score <= ?"
            params.append(max_score)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        if tags:
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f"%{tag}%")
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        return [self._row_to_record(row) for row in rows]
    
    def _row_to_record(self, row: sqlite3.Row) -> ExperienceRecord:
        """Convert database row to ExperienceRecord."""
        data = dict(row)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["experience_type"] = ExperienceType(data["experience_type"])
        data["problem_skills"] = json.loads(data["problem_skills"] or "[]")
        data["skill_scores"] = json.loads(data["skill_scores"] or "{}")
        data["error_patterns"] = json.loads(data["error_patterns"] or "[]")
        data["optimization_opportunities"] = json.loads(data["optimization_opportunities"] or "[]")
        data["environment"] = json.loads(data["environment"] or "{}")
        data["tags"] = json.loads(data["tags"] or "[]")
        
        if data.get("execution_trace"):
            et = json.loads(data["execution_trace"])
            et["started_at"] = datetime.fromisoformat(et["started_at"])
            if et.get("completed_at"):
                et["completed_at"] = datetime.fromisoformat(et["completed_at"])
            data["execution_trace"] = ExecutionTrace(**et)
        
        if data.get("test_results"):
            tr = json.loads(data["test_results"])
            tr["test_results"] = [RecorderTestResult(**r) for r in tr["test_results"]]
            data["test_results"] = TestSuiteResult(**tr)
        
        return ExperienceRecord(**data)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get recorder statistics."""
        with sqlite3.connect(self._db_path) as conn:
            # Total count
            total = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
            
            # Success rate
            success_rate = conn.execute(
                "SELECT AVG(CAST(success AS REAL)) FROM experiences"
            ).fetchone()[0] or 0
            
            # By type
            by_type = conn.execute(
                "SELECT experience_type, COUNT(*) FROM experiences GROUP BY experience_type"
            ).fetchall()
            
            # By domain
            by_domain = conn.execute(
                "SELECT problem_domain, COUNT(*) FROM experiences GROUP BY problem_domain"
            ).fetchall()
            
            # Average score
            avg_score = conn.execute(
                "SELECT AVG(score) FROM experiences"
            ).fetchone()[0] or 0
            
            # Recent activity (last 24h)
            recent = conn.execute(
                "SELECT COUNT(*) FROM experiences WHERE timestamp >= datetime('now', '-1 day')"
            ).fetchone()[0]
        
        return {
            "total_experiences": total,
            "total_recorded": self._total_recorded,
            "total_flushed": self._total_flushed,
            "buffer_size": len(self._buffer),
            "success_rate": success_rate,
            "average_score": avg_score,
            "recent_24h": recent,
            "by_type": {t: c for t, c in by_type},
            "by_domain": {d: c for d, c in by_domain},
            "storage_path": str(self.storage_path),
            "retention_days": self.retention_days,
        }
    
    async def cleanup_old_records(self):
        """Remove records older than retention period."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM experiences WHERE timestamp < datetime('now', ?)",
                (f"-{self.retention_days} days",)
            )
            deleted = cursor.rowcount
            conn.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old experience records")
        
        return deleted
    
    def on_recorded(self, callback: Callable[[ExperienceRecord], Awaitable[None]]):
        """Register callback for each recorded experience."""
        self._on_recorded.append(callback)
    
    def on_flushed(self, callback: Callable[[List[ExperienceRecord]], Awaitable[None]]):
        """Register callback for batch flushes."""
        self._on_flushed.append(callback)