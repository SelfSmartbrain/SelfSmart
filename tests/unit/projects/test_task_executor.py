"""
Unit tests for the TaskExecutor module.
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.projects.task_executor import TaskExecutor, TaskResult


class TestTaskExecutor:
    """Test cases for the TaskExecutor class."""

    def test_init(self):
        """Test initialization of TaskExecutor."""
        executor = TaskExecutor()
        assert isinstance(executor, TaskExecutor)
        assert hasattr(executor, '_active_tasks')
        assert isinstance(executor._active_tasks, dict)

    @pytest.mark.asyncio
    async def test_execute_task_generic(self):
        """Test executing a generic task."""
        executor = TaskExecutor()
        task_id = uuid.uuid4()
        payload = {
            "task_type": "generic",
            "data": "test data"
        }
        
        result = await executor.execute_task(task_id, payload)
        
        assert isinstance(result, TaskResult)
        assert result.task_id == task_id
        assert result.status == "success"
        assert isinstance(result.output, dict)
        assert "message" in result.output
        assert result.execution_time_ms >= 0
        assert result.executed_at is not None

    @pytest.mark.asyncio
    async def test_execute_task_code(self):
        """Test executing a code task."""
        executor = TaskExecutor()
        task_id = uuid.uuid4()
        payload = {
            "task_type": "code_execution",
            "code": "print('hello world')",
            "language": "python"
        }
        
        result = await executor.execute_task(task_id, payload)
        
        assert isinstance(result, TaskResult)
        assert result.task_id == task_id
        assert result.status == "success"
        assert isinstance(result.output, dict)
        assert "output" in result.output
        assert "exit_code" in result.output
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_task_api(self):
        """Test executing an API task."""
        executor = TaskExecutor()
        task_id = uuid.uuid4()
        payload = {
            "task_type": "api_call",
            "url": "https://api.example.com/data",
            "method": "GET"
        }
        
        result = await executor.execute_task(task_id, payload)
        
        assert isinstance(result, TaskResult)
        assert result.task_id == task_id
        assert result.status == "success"
        assert isinstance(result.output, dict)
        assert "status_code" in result.output
        assert "url" in result.output
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_task_data(self):
        """Test executing a data processing task."""
        executor = TaskExecutor()
        task_id = uuid.uuid4()
        payload = {
            "task_type": "data_processing",
            "data_size_mb": 5,
            "operation": "transform"
        }
        
        result = await executor.execute_task(task_id, payload)
        
        assert isinstance(result, TaskResult)
        assert result.task_id == task_id
        assert result.status == "success"
        assert isinstance(result.output, dict)
        assert "processed_mb" in result.output
        assert "operation" in result.output
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_task_research(self):
        """Test executing a research task."""
        executor = TaskExecutor()
        task_id = uuid.uuid4()
        payload = {
            "task_type": "research",
            "query": "machine learning algorithms",
            "sources": ["web", "knowledge_base"]
        }
        
        result = await executor.execute_task(task_id, payload)
        
        assert isinstance(result, TaskResult)
        assert result.task_id == task_id
        assert result.status == "success"
        assert isinstance(result.output, dict)
        assert "query" in result.output
        assert "sources_consulted" in result.output
        assert "findings_count" in result.output
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_task_empty_payload(self):
        """Test executing a task with empty payload."""
        executor = TaskExecutor()
        task_id = uuid.uuid4()
        payload = {}
        
        with pytest.raises(ValueError, match="Task payload cannot be empty"):
            await executor.execute_task(task_id, payload)

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancelling a task."""
        executor = TaskExecutor()
        task_id = uuid.uuid4()
        
        # Initially no task should be active
        result = await executor.cancel_task(task_id)
        assert result is False
        
        # Add a mock task to active tasks
        mock_task = asyncio.Task(asyncio.sleep(1))
        executor._active_tasks[task_id] = mock_task
        
        # Now cancelling should work
        result = await executor.cancel_task(task_id)
        assert result is True
        assert task_id not in executor._active_tasks

    def test_task_result_model(self):
        """Test the TaskResult model."""
        result = TaskResult(
            task_id=uuid.uuid4(),
            status="success",
            output={"key": "value"},
            executed_at=datetime.now(timezone.utc),
            execution_time_ms=150
        )
        
        assert isinstance(result.task_id, uuid.UUID)
        assert result.status == "success"
        assert result.output == {"key": "value"}
        assert result.execution_time_ms == 150
        assert isinstance(result.executed_at, datetime)
