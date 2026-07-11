"""Command-line entry point for the ModelX API server."""

from __future__ import annotations

import uvicorn

from src.config.settings import get_settings


def main() -> None:
    """Run the API using the configured host, port, and log level."""
    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug and settings.environment == "development",
    )


if __name__ == "__main__":
    main()
