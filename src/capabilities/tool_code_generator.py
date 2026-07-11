from __future__ import annotations

import json
from typing import Any, Dict

from src.config.logging import get_logger
from src.capabilities.tool_spec_generator import ToolSpec

logger = get_logger(__name__)

class ToolCodeGenerator:
    """
    Generates raw python source code for tools based on a ToolSpec.
    """
    
    def __init__(self, llm_client: Any):
        """
        Initialize with an LLM client capable of text generation.
        """
        self.llm_client = llm_client

    async def generate_code(self, spec: ToolSpec) -> Dict[str, str]:
        """
        Generate tool code (tool.py, tests.py, requirements.txt) from a ToolSpec.
        """
        logger.info(f"Generating code for tool spec: {spec.name}")
        prompt = self._build_prompt(spec)
        
        try:
            # Assumes llm_client has an async generate_text method
            response_text = await self.llm_client.generate_text(prompt)
            return self._parse_code_blocks(response_text)
        except Exception as e:
            logger.error(f"Failed to generate code for tool spec {spec.name}: {e}")
            raise

    def _build_prompt(self, spec: ToolSpec) -> str:
        spec_json = spec.model_dump_json(indent=2)
        return (
            f"Generate the raw source code for the following tool specification:\n"
            f"{spec_json}\n\n"
            f"Provide the output strictly as a JSON object with the following keys exactly: "
            f"'tool.py', 'tests.py', and 'requirements.txt'. The values should be the raw string content "
            f"for each respective file without any markdown wrappers inside the values."
        )

    def _parse_code_blocks(self, text: str) -> Dict[str, str]:
        """
        Safely extract and parse the JSON containing the file code blocks from the LLM response.
        """
        text = text.strip()
        # Remove potential markdown formatting
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        parsed = json.loads(text.strip())
        
        required_keys = {"tool.py", "tests.py", "requirements.txt"}
        missing_keys = required_keys - set(parsed.keys())
        if missing_keys:
            raise ValueError(f"Missing expected file keys in LLM response: {missing_keys}")
            
        return {
            "tool.py": parsed["tool.py"],
            "tests.py": parsed["tests.py"],
            "requirements.txt": parsed["requirements.txt"]
        }
