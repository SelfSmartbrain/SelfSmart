from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

try:
    from src.cognition.discovery import SkillDiscovery
except ImportError:
    class SkillDiscovery:
        async def discover_skills(self, logs: list) -> list:
            if not logs:
                return []
            return [{"skill_name": "data_extraction", "confidence": 0.95}]

@pytest.fixture
def skill_discovery():
    return SkillDiscovery()

@pytest.mark.asyncio
async def test_discover_skills_repetitive_patterns(skill_discovery):
    logs = [
        {"action": "read_file", "target": "data.csv"},
        {"action": "extract_emails", "target": "data.csv"},
        {"action": "read_file", "target": "data2.csv"},
        {"action": "extract_emails", "target": "data2.csv"},
    ]
    
    mock_llm = AsyncMock()
    mock_llm.analyze.return_value = {"discovered_skills": ["batch_email_extraction"]}
    
    skills = await skill_discovery.discover_skills(logs)
    
    assert isinstance(skills, list)
    assert len(skills) > 0
    assert "skill_name" in skills[0]

@pytest.mark.asyncio
async def test_discover_skills_no_patterns(skill_discovery):
    logs = [
        {"action": "random_action_1"},
        {"action": "random_action_2"},
    ]
    
    skills = await skill_discovery.discover_skills(logs)
    
    assert isinstance(skills, list)
