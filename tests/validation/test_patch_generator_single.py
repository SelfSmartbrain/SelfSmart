"""
Test PatchGenerator with a single simple task.
Task: Add a docstring to a function.
"""
import asyncio
import os
from pathlib import Path
from src.coding.patch_generator import PatchGenerator
from src.coding.planner import ExecutionPlan, ExecutionStep, StepType, TaskType

async def test_patch_generator_single():
    """Test PatchGenerator with a single simple task."""
    
    print("Testing PatchGenerator with single task...")
    print("Task: Add a docstring to a function")
    print()
    
    try:
        # Initialize PatchGenerator with repository path
        repository_path = os.environ.get("MODELX_REPO_PATH", str(Path(__file__).parent.parent.parent))
        generator = PatchGenerator(repository_path=repository_path)
        print("✅ PatchGenerator initialized")
        print()
        
        # Create a simple execution plan
        plan = ExecutionPlan(
            task_type=TaskType.BUG_FIX,
            goal="Add a docstring to the calculate_sum function",
            steps=[
                ExecutionStep(
                    step_type=StepType.GENERATE,
                    description="Generate docstring for calculate_sum function",
                    file_path="src/coding/example.py",
                    parameters={
                        "function_name": "calculate_sum",
                        "function_code": "def calculate_sum(a, b):\n    return a + b"
                    }
                )
            ]
        )
        
        print("Generated execution plan:")
        print(f"  Task: {plan.goal}")
        print(f"  Steps: {len(plan.steps)}")
        print()
        
        # Generate patch
        print("Generating patch...")
        patch = await generator.generate_patch(plan)
        
        print("✅ Patch generated successfully!")
        print()
        print("Patch details:")
        print(f"  Confidence: {patch.confidence:.2f}")
        print(f"  File changes: {len(patch.file_changes)}")
        print()
        if patch.file_changes:
            print("Generated changes:")
            for i, change in enumerate(patch.file_changes):
                print(f"  Change {i+1}:")
                print(f"    File: {change.file_path}")
                print(f"    Operation: {change.operation}")
                if change.new_content:
                    print(f"    New content preview: {change.new_content[:200]}...")
        else:
            print("No file changes generated")
        print()
        print("Metadata:")
        for key, value in patch.metadata.items():
            print(f"  {key}: {value}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}")
        print(f"Message: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
        print("FAILURE: PatchGenerator test failed")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_patch_generator_single())
    exit(0 if result else 1)
