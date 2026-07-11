"""
Report generator tool for the Autonomous Agent Platform.

Generates structured reports in Markdown or JSON format from
a title and a list of sections.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.tools.base import AgentTool

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class ReportSection(BaseModel):
    """A single section of a report."""

    heading: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Section heading",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Section body content (Markdown supported)",
    )
    level: int = Field(
        default=2,
        ge=1,
        le=6,
        description="Heading level (1–6, maps to # through ######)",
    )


class ReportGeneratorInput(BaseModel):
    """Input schema for ReportGeneratorTool."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Report title",
    )
    sections: list[ReportSection] = Field(
        ...,
        min_length=1,
        description="List of report sections",
    )
    format: Literal["markdown", "json"] = Field(
        default="markdown",
        description="Output format: 'markdown' or 'json'",
    )
    include_toc: bool = Field(
        default=True,
        description="Include a table of contents (Markdown only)",
    )
    include_timestamp: bool = Field(
        default=True,
        description="Include a generated-at timestamp",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class ReportGeneratorTool(AgentTool):
    """Generate structured reports in Markdown or JSON format.

    Accepts a title and a list of sections, each with a heading and
    content body.  The Markdown output includes an optional table of
    contents and a generation timestamp.

    Example usage::

        tool = ReportGeneratorTool()
        result = await tool._arun(
            title="Research Summary",
            sections=[
                {"heading": "Introduction", "content": "..."},
                {"heading": "Methods", "content": "..."},
            ],
            format="markdown",
        )
    """

    name: str = "report_generator"
    description: str = (
        "Generate structured reports in Markdown or JSON format from "
        "a title and a list of sections."
    )
    args_schema: type[BaseModel] = ReportGeneratorInput
    max_retries: int = 0
    timeout_seconds: float = 30.0

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Generate a report from the given inputs.

        Args:
            **kwargs: Validated fields from :class:`ReportGeneratorInput`.

        Returns:
            A dict with ``title``, ``format``, ``content`` (the rendered
            report string), ``section_count``, and ``character_count``.
        """
        title: str = kwargs["title"]
        sections_raw: list[dict[str, Any]] = kwargs["sections"]
        output_format: str = kwargs.get("format", "markdown")
        include_toc: bool = kwargs.get("include_toc", True)
        include_timestamp: bool = kwargs.get("include_timestamp", True)

        log = logger.bind(
            tool=self.name,
            title=title,
            section_count=len(sections_raw),
            format=output_format,
        )
        log.debug("report_generator.start")

        # Parse sections (may arrive as dicts from the LLM)
        sections = [
            ReportSection(**s) if isinstance(s, dict) else s
            for s in sections_raw
        ]

        timestamp = datetime.now(timezone.utc).isoformat()

        if output_format == "json":
            content = self._render_json(title, sections, timestamp, include_timestamp)
        else:
            content = self._render_markdown(title, sections, timestamp, include_toc, include_timestamp)

        result: dict[str, Any] = {
            "title": title,
            "format": output_format,
            "content": content,
            "section_count": len(sections),
            "character_count": len(content),
        }

        log.info(
            "report_generator.complete",
            char_count=len(content),
            section_count=len(sections),
        )

        return result

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    @staticmethod
    def _render_markdown(
        title: str,
        sections: list[ReportSection],
        timestamp: str,
        include_toc: bool,
        include_timestamp: bool,
    ) -> str:
        """Render the report as a Markdown document.

        Args:
            title: Report title.
            sections: List of :class:`ReportSection` objects.
            timestamp: ISO-format generation timestamp.
            include_toc: Whether to insert a table of contents.
            include_timestamp: Whether to include the timestamp.

        Returns:
            A complete Markdown string.
        """
        lines: list[str] = []

        # Title
        lines.append(f"# {title}")
        lines.append("")

        # Timestamp
        if include_timestamp:
            lines.append(f"*Generated: {timestamp}*")
            lines.append("")

        # Table of contents
        if include_toc and len(sections) > 1:
            lines.append("## Table of Contents")
            lines.append("")
            for i, section in enumerate(sections, start=1):
                # Create an anchor-safe slug
                slug = (
                    section.heading.lower()
                    .replace(" ", "-")
                    .replace(".", "")
                    .replace(",", "")
                )
                lines.append(f"{i}. [{section.heading}](#{slug})")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Sections
        for section in sections:
            prefix = "#" * section.level
            lines.append(f"{prefix} {section.heading}")
            lines.append("")
            lines.append(section.content)
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*End of report: {title}*")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _render_json(
        title: str,
        sections: list[ReportSection],
        timestamp: str,
        include_timestamp: bool,
    ) -> str:
        """Render the report as a JSON string.

        Args:
            title: Report title.
            sections: List of :class:`ReportSection` objects.
            timestamp: ISO-format generation timestamp.
            include_timestamp: Whether to include the timestamp.

        Returns:
            A pretty-printed JSON string.
        """
        payload: dict[str, Any] = {
            "title": title,
            "sections": [
                {
                    "heading": s.heading,
                    "content": s.content,
                    "level": s.level,
                }
                for s in sections
            ],
        }

        if include_timestamp:
            payload["generated_at"] = timestamp

        return json.dumps(payload, indent=2, ensure_ascii=False)
