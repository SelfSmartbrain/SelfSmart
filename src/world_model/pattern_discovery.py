from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class DiscoveredPattern(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    pattern_type: str  # SEQUENCE, FACT, ANTI_PATTERN
    description: str
    elements: List[str]
    frequency: int
    confidence: float = Field(ge=0.0, le=1.0)
    source_references: List[str]
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PatternDiscoveryEngine:
    """
    Scans through historical research tracks, failure analyses, skills, and tools
    to discover recurring sequences and facts.
    """

    def __init__(self, llm_client: Any) -> None:
        self.llm_client = llm_client

    async def discover_patterns(
        self,
        historical_tracks: List[Dict[str, Any]],
        failure_analyses: List[Dict[str, Any]],
        skills: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> List[DiscoveredPattern]:
        logger.info("Starting pattern discovery across historical data, failures, skills, and tools.")
        try:
            patterns: List[DiscoveredPattern] = []

            # Step 1: Discover sequences from tracks and tools
            sequence_patterns = await self._scan_for_sequences(historical_tracks, tools)
            patterns.extend(sequence_patterns)

            # Step 2: Discover facts and anti-patterns from failures and skills
            fact_patterns = await self._scan_for_facts(failure_analyses, skills)
            patterns.extend(fact_patterns)

            logger.info(f"Discovered {len(patterns)} total patterns.")
            return patterns
        except Exception as e:
            logger.error(f"Error discovering patterns: {e}")
            raise

    async def _scan_for_sequences(
        self, tracks: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        logger.debug("Scanning for recurring tool usage and execution sequences.")
        try:
            patterns: List[DiscoveredPattern] = []
            
            # Extract tool usage sequences from tracks
            tool_sequences: Dict[str, int] = {}
            for track in tracks:
                track_tools = track.get("tools_used", [])
                if len(track_tools) >= 2:
                    sequence_key = " -> ".join(track_tools)
                    tool_sequences[sequence_key] = tool_sequences.get(sequence_key, 0) + 1
            
            # Create patterns for frequent sequences
            for sequence, count in tool_sequences.items():
                if count >= 3:  # Minimum frequency threshold
                    pattern = DiscoveredPattern(
                        pattern_type="SEQUENCE",
                        description=f"Recurring tool sequence: {sequence}",
                        elements=sequence.split(" -> "),
                        frequency=count,
                        confidence=min(0.9, 0.5 + (count * 0.1)),
                        source_references=[f"track_{i}" for i in range(min(count, 5))]
                    )
                    patterns.append(pattern)
            
            return patterns
        except Exception as e:
            logger.error(f"Error in sequence scanning: {e}")
            raise

    async def _scan_for_facts(
        self, failures: List[Dict[str, Any]], skills: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        logger.debug("Scanning for recurring facts and anti-patterns.")
        try:
            patterns: List[DiscoveredPattern] = []
            
            # Extract common failure patterns
            failure_types: Dict[str, int] = {}
            for failure in failures:
                error_type = failure.get("error_type", "unknown")
                failure_types[error_type] = failure_types.get(error_type, 0) + 1
            
            for error_type, count in failure_types.items():
                if count >= 2:
                    pattern = DiscoveredPattern(
                        pattern_type="ANTI_PATTERN",
                        description=f"Recurring failure type: {error_type}",
                        elements=[error_type],
                        frequency=count,
                        confidence=min(0.85, 0.4 + (count * 0.15)),
                        source_references=[f"failure_{i}" for i in range(min(count, 3))]
                    )
                    patterns.append(pattern)
            
            # Extract successful skill patterns
            skill_patterns: Dict[str, int] = {}
            for skill in skills:
                skill_name = skill.get("name", "unknown")
                if skill.get("success_rate", 0) > 0.8:
                    skill_patterns[skill_name] = skill_patterns.get(skill_name, 0) + 1
            
            for skill_name, count in skill_patterns.items():
                if count >= 2:
                    pattern = DiscoveredPattern(
                        pattern_type="FACT",
                        description=f"High-performing skill: {skill_name}",
                        elements=[skill_name],
                        frequency=count,
                        confidence=min(0.9, 0.5 + (count * 0.1)),
                        source_references=[f"skill_{i}" for i in range(min(count, 3))]
                    )
                    patterns.append(pattern)
            
            return patterns
        except Exception as e:
            logger.error(f"Error in fact scanning: {e}")
            raise

    async def validate_pattern(
        self, pattern: DiscoveredPattern, new_data: List[Dict[str, Any]]
    ) -> DiscoveredPattern:
        logger.info(f"Validating pattern {pattern.id} against new data.")
        try:
            # Cross-reference the pattern with new executions to update confidence
            matches = 0
            for data_point in new_data:
                data_str = str(data_point)
                if any(element.lower() in data_str.lower() for element in pattern.elements):
                    matches += 1
            
            if matches > 0:
                # Update confidence based on validation results
                validation_ratio = matches / len(new_data)
                pattern.confidence = min(1.0, pattern.confidence + (validation_ratio * 0.1))
                pattern.frequency += matches
                logger.debug(f"Pattern {pattern.id} validated with {matches} matches")
            else:
                # Decrease confidence if no matches found
                pattern.confidence = max(0.1, pattern.confidence - 0.1)
                logger.debug(f"Pattern {pattern.id} not found in new data, confidence decreased")
            
            return pattern
        except Exception as e:
            logger.error(f"Error validating pattern: {e}")
            raise
