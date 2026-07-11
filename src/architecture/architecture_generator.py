from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.architecture.improvement_hypothesis_generator import ArchitectureHypothesis
from src.db.repositories.architecture_candidate_repo import ArchitectureCandidateRepository

logger = get_logger(__name__)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ArchitectureCandidate(BaseModel):
    model_config = {"from_attributes": True}
    
    candidate_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    hypothesis_id: uuid.UUID
    source_code_path: str
    status: str = "generated"
    created_at: datetime = Field(default_factory=utc_now)

class ArchitectureGenerator:
    """
    Code generator that takes an ArchitectureHypothesis and generates Python source code 
    for new agent variants into a candidate_architecture/ directory, registering an 
    ArchitectureCandidate to the DB.
    """
    def __init__(self, output_dir: str = "candidate_architecture", llm_client: Any = None):
        self.output_dir = output_dir
        self.logger = get_logger(self.__class__.__name__)
        self.llm_client = llm_client
        self.settings = get_settings()

    async def generate_architecture(self, hypothesis: ArchitectureHypothesis) -> ArchitectureCandidate:
        self.logger.info(f"Generating architecture candidate for hypothesis {hypothesis.hypothesis_id}")
        
        # Ensure the candidate architecture directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        candidate_filename = f"variant_{hypothesis.hypothesis_id.hex[:8]}.py"
        candidate_path = os.path.join(self.output_dir, candidate_filename)
        
        # Generate source code using LLM
        source_code = await self._generate_source_code(hypothesis)
        
        # Write to file
        with open(candidate_path, "w") as f:
            f.write(source_code)
            
        self.logger.info(f"Generated source code written to {candidate_path}")
        
        candidate = ArchitectureCandidate(
            hypothesis_id=hypothesis.hypothesis_id,
            source_code_path=candidate_path
        )
        
        await self._register_candidate(candidate)
        
        return candidate

    async def _generate_source_code(self, hypothesis: ArchitectureHypothesis) -> str:
        """
        Generate Python source code for the new agent variant using LLM.
        """
        if self.llm_client:
            # Use LLM to generate code based on hypothesis
            prompt = self._build_generation_prompt(hypothesis)
            try:
                generated_code = await self._call_llm_for_code(prompt)
                return self._validate_and_format_code(generated_code)
            except Exception as e:
                self.logger.error(f"LLM code generation failed: {e}, falling back to template")
                return self._generate_template_code(hypothesis)
        else:
            # Fallback to template-based generation
            self.logger.warning("No LLM client provided, using template-based generation")
            return self._generate_template_code(hypothesis)

    def _build_generation_prompt(self, hypothesis: ArchitectureHypothesis) -> str:
        """Build the prompt for LLM code generation."""
        return f"""Generate a Python class that implements the following architectural improvement:

Hypothesis ID: {hypothesis.hypothesis_id}
Problem: {hypothesis.problem_description}
Proposed Solution: {hypothesis.proposed_solution}
Expected Impact: {hypothesis.expected_impact}

Requirements:
- The class should be async-compatible
- Include proper logging using structlog
- Follow Python best practices and type hints
- Include docstrings for all methods
- The class should be named 'GeneratedAgentVariant'
- Implement a 'run' method that executes the agent's core logic

Generate only the Python code, no explanations."""

    async def _call_llm_for_code(self, prompt: str) -> str:
        """Call the LLM to generate code."""
        # This would use the actual LLM client (e.g., Anthropic, OpenAI)
        # For now, return a structured response
        # In production, this would be:
        # response = await self.llm_client.ainvoke(prompt)
        # return response.content
        
        # Placeholder implementation
        return self._generate_template_code(None)

    def _validate_and_format_code(self, code: str) -> str:
        """Validate and format the generated code."""
        # Basic validation: ensure it's a complete Python class
        if "class GeneratedAgentVariant" not in code:
            raise ValueError("Generated code must include GeneratedAgentVariant class")
        if "async def run" not in code:
            raise ValueError("Generated code must include async run method")
        
        return code.strip()

    def _generate_template_code(self, hypothesis: Optional[ArchitectureHypothesis]) -> str:
        """Generate template-based code when LLM is unavailable."""
        if hypothesis:
            solution_desc = hypothesis.proposed_solution
            hypothesis_id = str(hypothesis.hypothesis_id)
        else:
            solution_desc = "Template implementation"
            hypothesis_id = "template"
            
        return f'''from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
from src.config.logging import get_logger

logger = get_logger(__name__)

class GeneratedAgentVariant:
    """
    Generated agent variant implementing architectural improvement.
    
    Hypothesis ID: {hypothesis_id}
    Solution: {solution_desc}
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {{}}
        self.logger = get_logger(self.__class__.__name__)
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the agent variant."""
        self.logger.info("Initializing generated agent variant")
        # Initialization logic here
        self._initialized = True
        
    async def run(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the agent's core logic."""
        if not self._initialized:
            await self.initialize()
            
        self.logger.info("Running generated agent variant")
        
        try:
            # Core implementation logic would go here
            result = {{
                "status": "success",
                "output": "Agent execution completed",
                "metrics": {{"execution_time": 0.1}}
            }}
            return result
        except Exception as e:
            self.logger.error(f"Agent execution failed: {{e}}")
            raise
            
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.info("Cleaning up agent variant resources")
        self._initialized = False
'''

    async def _register_candidate(self, candidate: ArchitectureCandidate) -> None:
        """
        Register the ArchitectureCandidate to the DB.
        """
        self.logger.info(f"Registering architecture candidate {candidate.candidate_id} to database.")
        # In production, this would use the repository to persist to DB
        # Example:
        # repo = ArchitectureCandidateRepository(db_session)
        # await repo.create(candidate)
