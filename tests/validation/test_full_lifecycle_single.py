"""
Test full lifecycle with a single task through RealTaskExecutor.
Task → Planner → PatchGenerator → CodeEditor → TestRunner
"""
import asyncio
from tests.validation.v31_executor import RealTaskExecutor, ExecutionContext

async def test_full_lifecycle_single():
    """Test full lifecycle with a single simple task."""
    
    print("Testing full lifecycle with single task...")
    print("Task: Add a docstring to a function in the ModelX codebase")
    print()
    
    try:
        # Create execution context
        context = ExecutionContext(
            repository_path="/Users/subh/Documents/ModelX",
            task_description="Add a docstring to the calculate_sum function in src/coding/example.py",
            task_type="bug_fix",
            ablation_config=None
        )
        
        print("Created execution context:")
        print(f"  Task: {context.task_description}")
        print(f"  Repository: {context.repository_path}")
        print()
        
        # Initialize RealTaskExecutor
        executor = RealTaskExecutor()
        print("✅ RealTaskExecutor initialized")
        print()
        
        # Execute task
        print("Executing task through full lifecycle...")
        print("  1. Repository Analyzer")
        print("  2. Planner")
        print("  3. PatchGenerator (LLM)")
        print("  4. CodeEditor")
        print("  5. TestRunner")
        print()
        
        result = await executor.execute_task(context)
        
        print("✅ Task execution completed!")
        print()
        print("Results:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Test Pass Rate: {result.get('test_pass_rate', 0):.2%}")
        print(f"  Patch Accepted: {result.get('patch_accepted', False)}")
        print(f"  Rollback Required: {result.get('rollback_required', False)}")
        print(f"  Planning Quality: {result.get('planning_quality', 0):.2f}")
        print(f"  Decision Quality: {result.get('decision_quality', 0):.2f}")
        print(f"  Latency: {result.get('latency_seconds', 0):.2f}s")
        print()
        
        if result.get('metadata'):
            metadata = result['metadata']
            print("Metadata:")
            if 'plan' in metadata:
                plan = metadata['plan']
                print(f"  Plan steps: {len(plan.get('steps', []))}")
            if 'execution_result' in metadata:
                exec_result = metadata['execution_result']
                print(f"  Steps executed: {exec_result.get('steps_executed', 0)}")
                print(f"  Changes made: {len(exec_result.get('changes_made', []))}")
                if exec_result.get('errors'):
                    print(f"  Errors: {exec_result['errors']}")
        
        print()
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}")
        print(f"Message: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
        print("FAILURE: Full lifecycle test failed")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_full_lifecycle_single())
    exit(0 if result else 1)
