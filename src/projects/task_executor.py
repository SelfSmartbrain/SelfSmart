from __future__ import annotations

import uuid
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class TaskResult(BaseModel):
    model_config = {"from_attributes": True}
    
    task_id: uuid.UUID
    status: str
    output: Any
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: int = 0

class TaskExecutor:
    def __init__(self):
        # Track active tasks for cancellation
        self._active_tasks: dict[uuid.UUID, asyncio.Task] = {}

    async def execute_task(self, task_id: uuid.UUID, payload: Dict[str, Any]) -> TaskResult:
        logger.info(f"Executing task {task_id} with payload {payload}")
        start_time = time.time()
        
        # Validate payload
        if not payload:
            raise ValueError("Task payload cannot be empty")
        
        task_type = payload.get("task_type", "generic")
        
        try:
            # Simulate different types of task execution based on task_type
            if task_type == "code_execution":
                result = await self._execute_code_task(payload)
            elif task_type == "api_call":
                result = await self._execute_api_task(payload)
            elif task_type == "data_processing":
                result = await self._execute_data_task(payload)
            elif task_type == "research":
                result = await self._execute_research_task(payload)
            else:
                # Default generic task
                result = await self._execute_generic_task(payload)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return TaskResult(
                task_id=task_id,
                status="success",
                output=result,
                execution_time_ms=execution_time_ms
            )
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Task {task_id} failed after {execution_time_ms}ms: {str(e)}")
            
            return TaskResult(
                task_id=task_id,
                status="failed",
                output={"error": str(e), "task_type": task_type},
                execution_time_ms=execution_time_ms
            )

    async def _execute_code_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate code execution task"""
        code = payload.get("code", "")
        language = payload.get("language", "python")
        
        # Simulate execution delay based on code complexity
        delay = min(len(code) * 0.001, 2.0)  # Max 2 seconds
        await asyncio.sleep(delay)
        
        return {
            "output": f"Executed {language} code ({len(code)} chars)",
            "exit_code": 0,
            "execution_time": delay
        }

    async def _execute_api_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate API call task"""
        url = payload.get("url", "")
        method = payload.get("method", "GET")
        
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        return {
            "status_code": 200,
            "response_size": 1024,
            "url": url,
            "method": method
        }

    async def _execute_data_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate data processing task"""
        data_size = payload.get("data_size_mb", 1)
        operation = payload.get("operation", "transform")
        
        # Simulate processing delay based on data size
        delay = min(data_size * 0.1, 5.0)  # Max 5 seconds
        await asyncio.sleep(delay)
        
        return {
            "processed_mb": data_size,
            "operation": operation,
            "throughput_mbps": data_size / delay if delay > 0 else 0
        }

    async def _execute_research_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate research task"""
        query = payload.get("query", "")
        sources = payload.get("sources", ["web", "knowledge_base"])
        
        # Simulate research delay
        await asyncio.sleep(1.0)
        
        return {
            "query": query,
            "sources_consulted": sources,
            "findings_count": len(sources) * 3,
            "confidence_score": 0.85
        }

    async def _execute_generic_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate generic task"""
        await asyncio.sleep(0.2)  # Base delay
        
        return {
            "message": "Generic task completed",
            "payload_keys": list(payload.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }

    async def cancel_task(self, task_id: uuid.UUID) -> bool:
        logger.info(f"Cancelling task {task_id}")
        if task_id in self._active_tasks:
            task = self._active_tasks.pop(task_id)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False
