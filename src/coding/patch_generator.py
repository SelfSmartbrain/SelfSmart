"""Patch generator for creating code changes from plans."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from .planner import ExecutionPlan, ExecutionStep, StepType
from .code_editor import FileChange


@dataclass
class GeneratedPatch:
    """Generated code patch."""
    file_changes: List[FileChange] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'file_changes': [
                {
                    'file_path': fc.file_path,
                    'operation': fc.operation,
                    'content': fc.content,
                    'line_start': fc.line_start,
                    'line_end': fc.line_end,
                    'old_content': fc.old_content,
                    'new_content': fc.new_content
                }
                for fc in self.file_changes
            ],
            'metadata': self.metadata,
            'confidence': self.confidence
        }


class PatchGenerator:
    """Generates code patches from execution plans."""

    def __init__(self, repository_path: str):
        self.repository_path = repository_path
        # Initialize LLM using existing ModelX pattern
        from src.config.settings import get_settings
        settings = get_settings()
        llm_kwargs = {
            "model": settings.anthropic_model,
            "api_key": settings.anthropic_api_key.get_secret_value(),
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }
        # Add custom base URL if using OpenRouter
        if settings.anthropic_base_url:
            llm_kwargs["base_url"] = settings.anthropic_base_url
        self.llm = ChatAnthropic(**llm_kwargs)

    async def generate_patch(self, plan: ExecutionPlan, context: Optional[Dict] = None) -> GeneratedPatch:
        """Generate patches from an execution plan."""
        context = context or {}
        patch = GeneratedPatch()
        patch.metadata = {
            'task_type': plan.task_type.value,
            'goal': plan.goal,
            'complexity': plan.complexity,
            'estimated_steps': plan.estimated_steps
        }

        # Generate patches based on plan steps
        for step in plan.steps:
            if step.step_type == StepType.GENERATE:
                file_changes = await self._generate_from_step(step, context)
                patch.file_changes.extend(file_changes)
            elif step.step_type == StepType.APPLY:
                # APPLY steps typically reference previously generated content
                pass

        # Calculate confidence based on plan completeness
        patch.confidence = self._calculate_confidence(plan, patch)

        return patch

    async def _generate_from_step(self, step: ExecutionStep, context: Dict) -> List[FileChange]:
        """Generate file changes from a single step."""
        file_changes = []

        if step.parameters.get('focus') == 'test_generation':
            content = await self._generate_test_with_llm(step.description, context)
            file_changes.append(FileChange(
                file_path=step.file_path or "tests/test_generated.py",
                operation='create',
                content=content
            ))
        elif step.parameters.get('focus') == 'error_analysis':
            # Analysis step - no file changes
            pass
        else:
            # Generic code generation using LLM
            if step.file_path:
                content = await self._generate_code_with_llm(step.description, context)
                file_changes.append(FileChange(
                    file_path=step.file_path,
                    operation='patch',
                    old_content=context.get('current_code', ''),
                    new_content=content
                ))

        return file_changes

    async def _generate_test_with_llm(self, description: str, context: Dict) -> str:
        """Generate test code using LLM."""
        prompt = f"""Generate a comprehensive test for the following task:

Task: {description}

Context:
- Repository structure: {context.get('repository_structure', 'Unknown')}
- Related files: {context.get('related_files', [])}

Requirements:
- Use pytest framework
- Include proper assertions
- Handle edge cases
- Add docstrings
- Make tests self-contained

Respond with ONLY the Python test code, no explanation or markdown."""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an expert test engineer. Respond with ONLY executable Python test code."),
            HumanMessage(content=prompt),
        ])

        code = str(response.content)
        return self._clean_code_response(code)

    async def _generate_code_with_llm(self, description: str, context: Dict) -> str:
        """Generate code using LLM."""
        current_code = context.get('current_code', '')
        prompt = f"""Generate code to accomplish the following task:

Task: {description}

Current code (if applicable):
{current_code if current_code else '[No existing code - create new implementation]'}

Context:
- File path: {context.get('file_path', 'Unknown')}
- Related files: {context.get('related_files', [])}
- Repository structure: {context.get('repository_structure', 'Unknown')}

Requirements:
- Write clean, maintainable code
- Follow existing code style
- Add docstrings
- Handle errors appropriately
- Maintain backward compatibility when modifying existing code

Respond with ONLY the code, no explanation or markdown."""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an expert software engineer. Respond with ONLY executable code."),
            HumanMessage(content=prompt),
        ])

        code = str(response.content)
        return self._clean_code_response(code)

    def _clean_code_response(self, code: str) -> str:
        """Clean LLM response to extract pure code."""
        # Strip markdown code blocks if present
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()
        return code

    def _calculate_confidence(self, plan: ExecutionPlan, patch: GeneratedPatch) -> float:
        """Calculate confidence score for the generated patch."""
        confidence = 0.5  # Base confidence

        # Increase confidence if plan has clear structure
        if plan.estimated_steps > 0:
            confidence += 0.1

        # Increase confidence if file changes are generated
        if len(patch.file_changes) > 0:
            confidence += 0.2

        # Increase confidence if context is provided
        if plan.context:
            confidence += 0.1

        # Cap at 1.0
        return min(confidence, 1.0)

    async def generate_bug_fix_patch(self, error_message: str, file_path: str, context: Dict) -> GeneratedPatch:
        """Generate a patch for bug fixing."""
        patch = GeneratedPatch()
        patch.metadata = {
            'task_type': 'bug_fix',
            'error_message': error_message,
            'file_path': file_path
        }

        # Generate fix based on error using LLM
        fix_code = await self._generate_fix_for_error(error_message, context)

        patch.file_changes.append(FileChange(
            file_path=file_path,
            operation='patch',
            old_content=context.get('current_code', ''),
            new_content=fix_code
        ))

        patch.confidence = 0.7
        return patch

    async def generate_feature_patch(self, feature_description: str, file_path: str, context: Dict) -> GeneratedPatch:
        """Generate a patch for feature development."""
        patch = GeneratedPatch()
        patch.metadata = {
            'task_type': 'feature_development',
            'feature_description': feature_description,
            'file_path': file_path
        }

        # Generate feature implementation using LLM
        feature_code = await self._generate_feature_code(feature_description, context)

        patch.file_changes.append(FileChange(
            file_path=file_path,
            operation='patch',
            old_content=context.get('current_code', ''),
            new_content=feature_code
        ))

        patch.confidence = 0.6
        return patch

    async def generate_refactor_patch(self, refactor_description: str, file_path: str, context: Dict) -> GeneratedPatch:
        """Generate a patch for refactoring."""
        patch = GeneratedPatch()
        patch.metadata = {
            'task_type': 'refactoring',
            'refactor_description': refactor_description,
            'file_path': file_path
        }

        # Generate refactored code using LLM
        refactored_code = await self._generate_refactored_code(refactor_description, context)

        patch.file_changes.append(FileChange(
            file_path=file_path,
            operation='patch',
            old_content=context.get('current_code', ''),
            new_content=refactored_code
        ))

        patch.confidence = 0.65
        return patch

    async def _generate_fix_for_error(self, error_message: str, context: Dict) -> str:
        """Generate fix code based on error message using LLM."""
        current_code = context.get('current_code', '')
        prompt = f"""Fix the following error in the code:

Error: {error_message}

Current code:
{current_code if current_code else '[No code provided]'}

Context:
- File path: {context.get('file_path', 'Unknown')}
- Related files: {context.get('related_files', [])}

Requirements:
- Fix the error without breaking existing functionality
- Add appropriate error handling
- Maintain code style
- Add comments explaining the fix

Respond with ONLY the fixed code, no explanation or markdown."""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an expert debugger. Respond with ONLY the fixed code."),
            HumanMessage(content=prompt),
        ])

        code = str(response.content)
        return self._clean_code_response(code)

    async def _generate_feature_code(self, feature_description: str, context: Dict) -> str:
        """Generate feature implementation code using LLM."""
        current_code = context.get('current_code', '')
        prompt = f"""Implement the following feature:

Feature: {feature_description}

Current code (if applicable):
{current_code if current_code else '[No existing code - create new implementation]'}

Context:
- File path: {context.get('file_path', 'Unknown')}
- Related files: {context.get('related_files', [])}
- Repository structure: {context.get('repository_structure', 'Unknown')}

Requirements:
- Write clean, maintainable code
- Follow existing patterns in the codebase
- Add comprehensive docstrings
- Handle edge cases
- Maintain backward compatibility

Respond with ONLY the implementation code, no explanation or markdown."""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an expert software architect. Respond with ONLY implementation code."),
            HumanMessage(content=prompt),
        ])

        code = str(response.content)
        return self._clean_code_response(code)

    async def _generate_refactored_code(self, refactor_description: str, context: Dict) -> str:
        """Generate refactored code using LLM."""
        current_code = context.get('current_code', '')
        prompt = f"""Refactor the following code:

Refactoring goal: {refactor_description}

Current code:
{current_code}

Context:
- File path: {context.get('file_path', 'Unknown')}
- Related files: {context.get('related_files', [])}

Requirements:
- Improve code structure and readability
- Reduce complexity
- Maintain exact same functionality
- Follow best practices
- Add comments explaining improvements

Respond with ONLY the refactored code, no explanation or markdown."""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an expert code refactoring specialist. Respond with ONLY refactored code."),
            HumanMessage(content=prompt),
        ])

        code = str(response.content)
        return self._clean_code_response(code)
