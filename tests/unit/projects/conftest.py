"""
Local conftest for project tests that avoids database initialization issues.
"""
import sys
from unittest.mock import MagicMock

# Mock the problematic database imports before they're loaded
sys.modules['src.db.models'] = MagicMock()
sys.modules['src.db'] = MagicMock()
sys.modules['src.db.session'] = MagicMock()

# Mark that we're using mocks
import os
os.environ['TESTING'] = '1'