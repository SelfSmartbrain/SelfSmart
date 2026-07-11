"""Adversarial checks for honest objective-template labeling."""

import pytest

from src.autonomy.objective_manager import ObjectiveManager


TEMPLATES = [
    "Refine and optimize",
    "Validate and test",
    "Document and share",
    "Scale and deploy",
    "Monitor and maintain",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("pattern_index, prefix", enumerate(TEMPLATES))
async def test_declared_template_is_used(pattern_index, prefix):
    """The public mechanism must behave exactly like the declared template API."""
    seed = "Audit the RAG pipeline for stale embeddings"
    manager = ObjectiveManager()
    objective = await manager.set_objective(seed)
    await manager.complete_objective(objective.objective_id)

    suggested = await manager.suggest_followup_template(
        context={"follow_up_pattern": pattern_index}
    )

    assert suggested is not None
    assert suggested.description == f"{prefix}: {seed}"
    assert suggested.metadata["autonomous"] is False
    assert suggested.metadata["generation_method"] == "template_based"
    assert suggested.metadata["source_objective_id"] == objective.objective_id


def test_public_api_does_not_claim_autonomous_generation():
    """The removed method name must not continue to advertise a false mechanism."""
    manager = ObjectiveManager()

    assert hasattr(manager, "suggest_followup_template")
    assert hasattr(manager, "should_suggest_followup_template")
    assert not hasattr(manager, "generate_next_objective")
    assert not hasattr(manager, "should_generate_autonomous_objective")
