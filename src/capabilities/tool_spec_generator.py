from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from src.config.logging import get_logger

logger = get_logger(__name__)

class CapabilityGap(BaseModel):
    model_config = {"from_attributes": True}
    
    id: str
    description: str
    context: Optional[str] = None

class ToolSpec(BaseModel):
    model_config = {"from_attributes": True}
    
    name: str
    description: str
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    dependencies: List[str]

class ToolSpecGenerator:
    """
    Generates a structured ToolSpec using an LLM based on a provided CapabilityGap.
    """
    
    def __init__(self, llm_client: Any):
        """
        Initialize with an LLM client capable of text generation.
        """
        self.llm_client = llm_client

    async def generate_spec(self, gap: CapabilityGap) -> ToolSpec:
        """
        Generate a ToolSpec for a given CapabilityGap.
        """
        logger.info(f"Generating tool spec for gap: {gap.id}")
        prompt = self._build_prompt(gap)
        
        try:
            # Assumes llm_client has an async generate_text method
            response_text = await self.llm_client.generate_text(prompt)
            spec_data = self._parse_json(response_text)
            return ToolSpec.model_validate(spec_data)
        except Exception as e:
            logger.error(f"Failed to generate tool spec for gap {gap.id}: {e}")
            raise

    def _build_prompt(self, gap: CapabilityGap) -> str:
        return (
            f"Generate a structured JSON tool specification for the following capability gap:\n"
            f"Description: {gap.description}\n"
            f"Context: {gap.context or 'None'}\n\n"
            f"The JSON must strictly include 'name', 'description', 'inputs' (list of dicts containing 'name', 'type', 'description'), "
            f"'outputs' (list of dicts containing 'name', 'type', 'description'), and 'dependencies' (list of python package strings)."
        )

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """
        Safely extract and parse JSON from the LLM response text.
        """
        text = text.strip()
        # Remove potential markdown formatting
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text.strip())
