"""
SelfSmart AI Python SDK
A lightweight, typed client for integrating SelfSmart AI into your applications.
"""

import requests
from typing import Dict, Any, Optional, List


class SelfSmartClient:
    def __init__(self, base_url: str, api_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if api_token:
            self.session.headers.update({"Authorization": f"Bearer {api_token}"})

    def chat(self, message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a message to the chat API."""
        payload = {"message": message}
        if conversation_id:
            payload["conversation_id"] = conversation_id

        response = self.session.post(f"{self.base_url}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()

    def get_conversations(self) -> List[Dict[str, Any]]:
        """List user conversations."""
        response = self.session.get(f"{self.base_url}/api/conversations")
        response.raise_for_status()
        return response.json()