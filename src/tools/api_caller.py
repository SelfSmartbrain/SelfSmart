"""
HTTP API caller tool for the Autonomous Agent Platform.

Makes external HTTP requests using ``httpx`` with:
- URL validation (blocks internal/private IP ranges)
- Rate limiting (token bucket)
- Configurable method, headers, body, and timeout
"""

from __future__ import annotations

import asyncio
import ipaddress
import time
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.tools.base import AgentTool, ToolExecutionError

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class _TokenBucketRateLimiter:
    """Simple async-compatible token-bucket rate limiter.

    Attributes:
        rate: Tokens added per second.
        max_tokens: Bucket capacity.
    """

    def __init__(self, rate: float = 5.0, max_tokens: float = 10.0) -> None:
        self.rate = rate
        self.max_tokens = max_tokens
        self._tokens = max_tokens
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                # Calculate wait time for the next token
                wait = (1.0 - self._tokens) / self.rate
                await asyncio.sleep(wait)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_tokens, self._tokens + elapsed * self.rate)
        self._last_refill = now


# Module-level rate limiter (shared across all APICallerTool instances)
_rate_limiter = _TokenBucketRateLimiter(rate=5.0, max_tokens=10.0)

# ---------------------------------------------------------------------------
# Private IP ranges to block
# ---------------------------------------------------------------------------

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

_BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "metadata.google.internal",
    "169.254.169.254",
})


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class APICallerInput(BaseModel):
    """Input schema for APICallerTool."""

    url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Target URL for the HTTP request",
    )
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"] = Field(
        default="GET",
        description="HTTP method",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP request headers",
    )
    body: dict[str, Any] | None = Field(
        default=None,
        description="JSON request body (for POST/PUT/PATCH)",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Request timeout in seconds",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class APICallerTool(AgentTool):
    """Make HTTP requests to external APIs.

    Validates URLs to prevent SSRF attacks (blocks private/internal
    IPs and cloud metadata endpoints).  All requests pass through a
    token-bucket rate limiter.

    Example usage::

        tool = APICallerTool()
        result = await tool._arun(
            url="https://api.example.com/data",
            method="GET",
        )
    """

    name: str = "api_caller"
    description: str = (
        "Make HTTP requests to external APIs. Returns status code, "
        "response headers, and body. Blocks internal/private IPs."
    )
    args_schema: type[BaseModel] = APICallerInput
    timeout_seconds: float = 60.0

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute an HTTP request.

        Args:
            **kwargs: Validated fields from :class:`APICallerInput`.

        Returns:
            A dict with ``status_code``, ``headers``, ``body``,
            ``url``, ``method``, and ``elapsed_ms``.
        """
        url: str = kwargs["url"]
        method: str = kwargs.get("method", "GET")
        headers: dict[str, str] = kwargs.get("headers", {})
        body: dict[str, Any] | None = kwargs.get("body")
        timeout: int = kwargs.get("timeout", 30)

        log = logger.bind(tool=self.name, url=url, method=method)
        log.debug("api_caller.start")

        # --- URL validation ---
        self._validate_url(url)

        # --- Rate limit ---
        await _rate_limiter.acquire()

        # --- Make the request ---
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            request_kwargs: dict[str, Any] = {
                "method": method,
                "url": url,
                "headers": headers,
            }

            if body is not None and method in {"POST", "PUT", "PATCH"}:
                request_kwargs["json"] = body

            response = await client.request(**request_kwargs)

        # --- Format the response ---
        # Try to parse body as JSON; fall back to text
        try:
            response_body: Any = response.json()
        except Exception:
            response_body = response.text[:50_000]  # cap text size

        response_headers = dict(response.headers)

        result: dict[str, Any] = {
            "status_code": response.status_code,
            "headers": response_headers,
            "body": response_body,
            "url": str(response.url),
            "method": method,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
        }

        log.info(
            "api_caller.complete",
            status_code=response.status_code,
            elapsed_ms=result["elapsed_ms"],
        )

        return result

    # ------------------------------------------------------------------
    # URL validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_url(url: str) -> None:
        """Validate a URL and block requests to private/internal addresses.

        Args:
            url: The URL to validate.

        Raises:
            ToolExecutionError: If the URL targets a private, internal, or
                otherwise blocked destination.
        """
        parsed = urlparse(url)

        # Require HTTPS or HTTP scheme
        if parsed.scheme not in {"http", "https"}:
            raise ToolExecutionError(
                tool_name="api_caller",
                message=f"Unsupported URL scheme: {parsed.scheme!r}. Only HTTP/HTTPS allowed.",
            )

        hostname = parsed.hostname
        if not hostname:
            raise ToolExecutionError(
                tool_name="api_caller",
                message="URL has no hostname.",
            )

        # Block known dangerous hostnames
        if hostname.lower() in _BLOCKED_HOSTNAMES:
            raise ToolExecutionError(
                tool_name="api_caller",
                message=f"Blocked hostname: {hostname!r}.",
            )

        # Resolve and check IP address
        try:
            addr = ipaddress.ip_address(hostname)
        except ValueError:
            # hostname is not a raw IP — resolve it.
            # We do a synchronous resolution here; it's fast and keeps
            # the validation path simple.
            import socket

            try:
                resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                ips = {ipaddress.ip_address(r[4][0]) for r in resolved}
            except socket.gaierror as e:
                # Can't resolve — BLOCK the request to prevent DNS rebinding attacks.
                # An attacker could register a domain that initially resolves to a public IP
                # but later resolves to a private IP.
                logger.warning("api_caller.dns_resolution_failed", hostname=hostname, error=str(e))
                raise ToolExecutionError(
                    tool_name="api_caller",
                    message=f"Blocked: {hostname!r} could not be resolved. DNS resolution required for security.",
                )

            for ip in ips:
                for network in _PRIVATE_NETWORKS:
                    if ip in network:
                        raise ToolExecutionError(
                            tool_name="api_caller",
                            message=f"Blocked: {hostname!r} resolves to private IP {ip}.",
                        )
            return

        # Direct IP — check against private ranges
        for network in _PRIVATE_NETWORKS:
            if addr in network:
                raise ToolExecutionError(
                    tool_name="api_caller",
                    message=f"Blocked private/internal IP: {addr}.",
                )


ApiCallerTool = APICallerTool
