import pytest
import os
from pathlib import Path

def test_feature_generation():
    """
    Test the new feature generation.
    
    This test ensures that the new feature is generated correctly and handles edge cases.
    """
    # Test case 1: Nominal case
    feature_path = os.path.join(Path(__file__).parent.parent, "ModelX", "new_feature.py")
    assert os.path.exists(feature_path)
    
    # Test case 2: Edge case - Feature file does not exist
    non_existent_feature_path = os.path.join(Path(__file__).parent.parent, "ModelX", "non_existent_feature.py")
    assert not os.path.exists(non_existent_feature_path)
    
    # Test case 3: Edge case - Feature file is empty
    empty_feature_path = os.path.join(Path(__file__).parent.parent, "ModelX", "empty_feature.py")
    open(empty_feature_path, "w").close()
    assert os.path.getsize(empty_feature_path) == 0
    os.remove(empty_feature_path)
    
    # Test case 4: Edge case - Feature file has syntax errors
    syntax_error_feature_path = os.path.join(Path(__file__).parent.parent, "ModelX", "syntax_error_feature.py")
    with open(syntax_error_feature_path, "w") as f:
        f.write("def feature():\n    return 'feature'")
    with pytest.raises(SyntaxError):
        import syntax_error_feature
    os.remove(syntax_error_feature_path)