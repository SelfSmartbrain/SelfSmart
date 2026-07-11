"""API Client for ModelX CLI."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from src.config.logging import get_logger

logger = get_logger(__name__)


class ModelXClient:
    """HTTP client for interacting with ModelX API."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize API client.
        
        Args:
            base_url: Base URL of ModelX API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(timeout=60.0)
        
        logger.info(f"Initialized ModelX client for {base_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle API response.
        
        Args:
            response: HTTP response
            
        Returns:
            Response JSON data
        """
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"API error: {e.response.status_code} - {e.response.text}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise Exception(f"Invalid JSON response: {e}")
    
    # ---------------------------------------------------------------------------
    # Goals API
    # ---------------------------------------------------------------------------
    
    def create_goal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new goal."""
        response = self.client.post(
            f"{self.base_url}/api/v1/goals",
            json=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def list_goals(self) -> List[Dict[str, Any]]:
        """List all goals."""
        response = self.client.get(
            f"{self.base_url}/api/v1/goals",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def get_goal(self, goal_id: str) -> Dict[str, Any]:
        """Get goal details."""
        response = self.client.get(
            f"{self.base_url}/api/v1/goals/{goal_id}",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def delete_goal(self, goal_id: str) -> None:
        """Delete a goal."""
        response = self.client.delete(
            f"{self.base_url}/api/v1/goals/{goal_id}",
            headers=self._get_headers()
        )
        self._handle_response(response)
    
    # ---------------------------------------------------------------------------
    # Tasks API
    # ---------------------------------------------------------------------------
    
    def create_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task."""
        response = self.client.post(
            f"{self.base_url}/api/v1/tasks",
            json=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def list_tasks(self, goal_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tasks."""
        params = {}
        if goal_id:
            params["goal_id"] = goal_id
        if status:
            params["status"] = status
        
        response = self.client.get(
            f"{self.base_url}/api/v1/tasks",
            params=params,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task details."""
        response = self.client.get(
            f"{self.base_url}/api/v1/tasks/{task_id}",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a task."""
        response = self.client.post(
            f"{self.base_url}/api/v1/tasks/{task_id}/execute",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    # ---------------------------------------------------------------------------
    # Memory API
    # ---------------------------------------------------------------------------
    
    def add_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a memory entry."""
        response = self.client.post(
            f"{self.base_url}/api/v1/memory",
            json=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memory."""
        response = self.client.get(
            f"{self.base_url}/api/v1/memory/search",
            params={"query": query, "limit": limit},
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def list_memories(self) -> List[Dict[str, Any]]:
        """List all memories."""
        response = self.client.get(
            f"{self.base_url}/api/v1/memory",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    # ---------------------------------------------------------------------------
    # Knowledge API
    # ---------------------------------------------------------------------------
    
    def add_knowledge(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add knowledge entry."""
        response = self.client.post(
            f"{self.base_url}/api/v1/knowledge",
            json=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        response = self.client.get(
            f"{self.base_url}/api/v1/knowledge/search",
            params={"query": query},
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    # ---------------------------------------------------------------------------
    # Meta-Learning API
    # ---------------------------------------------------------------------------
    
    def analyze_meta_learning(self) -> Dict[str, Any]:
        """Analyze learning patterns."""
        response = self.client.get(
            f"{self.base_url}/api/v1/meta/analyze",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """List learned strategies."""
        response = self.client.get(
            f"{self.base_url}/api/v1/meta/strategies",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    # ---------------------------------------------------------------------------
    # Reflections API
    # ---------------------------------------------------------------------------
    
    def create_reflection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a reflection."""
        response = self.client.post(
            f"{self.base_url}/api/v1/reflections",
            json=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def list_reflections(self) -> List[Dict[str, Any]]:
        """List all reflections."""
        response = self.client.get(
            f"{self.base_url}/api/v1/reflections",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    # ---------------------------------------------------------------------------
    # Autonomous API
    # ---------------------------------------------------------------------------
    
    def run_autonomous(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run autonomous execution."""
        response = self.client.post(
            f"{self.base_url}/api/v1/autonomous/run",
            json=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get autonomous execution status."""
        response = self.client.get(
            f"{self.base_url}/api/v1/autonomous/status/{execution_id}",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    # ---------------------------------------------------------------------------
    # Vision API (Phase 7)
    # ---------------------------------------------------------------------------
    
    def analyze_image(self, files: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze an image."""
        response = self.client.post(
            f"{self.base_url}/api/v1/vision/analyze",
            files=files,
            data=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def capture_web_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Capture screenshot from URL."""
        response = self.client.post(
            f"{self.base_url}/api/v1/vision/capture",
            json=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def detect_elements(self, files: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect elements in image."""
        response = self.client.post(
            f"{self.base_url}/api/v1/vision/detect-elements",
            files=files,
            data=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    # ---------------------------------------------------------------------------
    # Swarm API (Phase 8)
    # ---------------------------------------------------------------------------
    
    def submit_swarm_goal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a goal to the swarm."""
        response = self.client.post(
            f"{self.base_url}/api/v1/swarm/goals",
            json=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def get_swarm_goal_status(self, goal_id: str) -> Dict[str, Any]:
        """Get swarm goal status."""
        response = self.client.get(
            f"{self.base_url}/api/v1/swarm/goals/{goal_id}",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def get_swarm_metrics(self) -> Dict[str, Any]:
        """Get swarm metrics."""
        response = self.client.get(
            f"{self.base_url}/api/v1/swarm/status",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def scale_swarm(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Scale the swarm."""
        response = self.client.post(
            f"{self.base_url}/api/v1/swarm/scale",
            json=data,
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def initialize_swarm(self) -> Dict[str, Any]:
        """Initialize the swarm."""
        response = self.client.post(
            f"{self.base_url}/api/v1/swarm/initialize",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def shutdown_swarm(self) -> Dict[str, Any]:
        """Shutdown the swarm."""
        response = self.client.post(
            f"{self.base_url}/api/v1/swarm/shutdown",
            headers=self._get_headers()
        )
        return self._handle_response(response)
    
    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
