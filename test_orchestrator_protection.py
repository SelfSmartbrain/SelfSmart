#!/usr/bin/env python3
"""Quick verification that orchestrator is now in CRITICAL_PATHS."""

import sys
sys.path.insert(0, '/Users/subh/Documents/ModelX')

from src.safety.self_patch_safety_gate import SelfPatchSafetyGate
from src.coding.code_editor import FileChange

def test_orchestrator_in_critical_paths():
    """Verify orchestrator.py is in CRITICAL_PATHS."""
    gate = SelfPatchSafetyGate(repository_path="/Users/subh/Documents/ModelX")
    
    # Check if orchestrator.py is in CRITICAL_PATHS
    assert "src/agents/orchestrator.py" in gate.CRITICAL_PATHS, "orchestrator.py not in CRITICAL_PATHS"
    assert "src/agents/" in gate.CRITICAL_PATHS, "src/agents/ not in CRITICAL_PATHS"
    
    print("✓ orchestrator.py is in CRITICAL_PATHS")
    print("✓ src/agents/ is in CRITICAL_PATHS")
    
    # Test that a patch targeting orchestrator is marked as critical
    patch = FileChange(
        file_path="src/agents/orchestrator.py",
        operation="patch",
        old_content="",
        new_content="# malicious change",
    )
    
    safety_check = gate.perform_safety_check([patch])
    
    assert safety_check.safety_level.value == "critical", f"Expected critical, got {safety_check.safety_level.value}"
    assert safety_check.requires_human_approval is True, "Should require human approval"
    assert safety_check.can_apply is False, "Should not be auto-approvable without human approval"
    
    print("✓ Patch targeting orchestrator is marked as CRITICAL")
    print("✓ Patch requires human approval")
    print("✓ Patch cannot be auto-applied")
    
    return True

if __name__ == "__main__":
    try:
        test_orchestrator_in_critical_paths()
        print("\n✅ All checks passed - orchestrator protection is working")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
