"""Adversarial tests for assumption checks against observable state."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, text

from src.governance.assumption_detector import (
    Assumption,
    AssumptionDetector,
    AssumptionType,
)


class AsyncConnectionAdapter:
    """Expose a real synchronous SQLAlchemy connection as an async test session."""

    def __init__(self, connection):
        self.connection = connection

    async def execute(self, statement):
        return self.connection.execute(statement)


@pytest.mark.asyncio
async def test_false_assumption_is_detected_as_false():
    """A row-count claim must be checked against a real seeded database."""
    detector = AssumptionDetector()
    assumption = Assumption(
        assumption_type=AssumptionType.RESOURCE,
        description="progress_records has fewer than 10 rows",
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        connection.execute(text("CREATE TABLE progress_records (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text("INSERT INTO progress_records (id) VALUES (:id)"),
            [{"id": row_id} for row_id in range(1, 13)],
        )
        connection.commit()

        result = await detector.test_assumption(
            assumption,
            db_session=AsyncConnectionAdapter(connection),
        )

    assert result.tested is True
    assert result.test_result is False
    assert result.verification_method == "database"
    assert result.metadata["verification_details"]["actual_count"] == 12


@pytest.mark.asyncio
async def test_assumption_flips_on_retest_after_state_changes():
    """Retesting must observe a changed row count rather than reuse stale state."""
    detector = AssumptionDetector()
    assumption = Assumption(
        assumption_type=AssumptionType.RESOURCE,
        description="progress_records has fewer than 10 rows",
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        connection.execute(text("CREATE TABLE progress_records (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text("INSERT INTO progress_records (id) VALUES (:id)"),
            [{"id": row_id} for row_id in range(1, 13)],
        )
        connection.commit()
        session = AsyncConnectionAdapter(connection)

        first = await detector.test_assumption(assumption, db_session=session)

        connection.execute(text("DELETE FROM progress_records WHERE id > 5"))
        connection.commit()
        retested = await detector.test_assumption(assumption, db_session=session)

    assert first is retested
    assert retested.test_result is True
    assert retested.verification_method == "database"
    assert retested.metadata["verification_details"]["actual_count"] == 5


@pytest.mark.asyncio
async def test_database_unavailable_uses_transparent_value_aware_fallback():
    """A database failure must be visible and the fallback must compare values."""
    detector = AssumptionDetector()
    assumption = Assumption(
        assumption_type=AssumptionType.RESOURCE,
        description="progress_records has fewer than 10 rows",
    )
    unavailable_session = AsyncMock()
    unavailable_session.execute.side_effect = ConnectionError("database unavailable")

    first = await detector.test_assumption(
        assumption,
        test_context={"available_resources": {"progress_records": 12}},
        db_session=unavailable_session,
    )
    assert first.test_result is False
    assert first.verification_method == "context_fallback"
    assert "ConnectionError" in first.metadata["verification_error"]

    retested = await detector.test_assumption(
        assumption,
        test_context={"available_resources": {"progress_records": 5}},
        db_session=unavailable_session,
    )
    assert retested.test_result is True
    assert retested.verification_method == "context_fallback"
    assert retested.metadata["verification_details"]["actual_count"] == 5


@pytest.mark.asyncio
async def test_supported_row_count_comparisons():
    """Natural-language comparison variants must map to the right operators."""
    detector = AssumptionDetector()
    cases = [
        ("records has at least 5 rows", 5, True),
        ("records has at most 5 rows", 6, False),
        ("records has more than 5 rows", 6, True),
        ("records has exactly 5 rows", 5, True),
    ]

    for description, actual_count, expected in cases:
        assumption = Assumption(
            assumption_type=AssumptionType.RESOURCE,
            description=description,
        )
        result = await detector.test_assumption(
            assumption,
            test_context={"available_resources": {"records": actual_count}},
        )
        assert result.test_result is expected
        assert result.verification_method == "context_fallback"
