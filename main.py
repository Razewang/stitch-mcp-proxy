"""Prefect Horizon entrypoint for a secured Google Stitch MCP proxy."""

from __future__ import annotations

import hashlib
import logging
import os
from importlib.metadata import PackageNotFoundError, version

from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server import create_proxy

UPSTREAM_URL = "https://stitch.googleapis.com/mcp"
API_KEY_ENV = "GOOGLE_API_KEY"
logger = logging.getLogger(__name__)


def _required_env(name: str) -> str:
    """Return a required environment variable or fail with a clear message."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            "Configure it as a secret in the deployment environment."
        )
    return value.strip()


def _fastmcp_version() -> str:
    """Return the installed FastMCP version without failing server startup."""
    try:
        return version("fastmcp")
    except PackageNotFoundError:
        return "unknown"


def _key_fingerprint(value: str) -> str:
    """Return a non-reversible identifier for comparing configured key values."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


# Clients connect only to this proxy. The Google API key is injected server-side
# and is never required in the downstream client's MCP configuration.
api_key = _required_env(API_KEY_ENV)
upstream_headers = {"X-Goog-Api-Key": api_key}

logger.warning(
    "Stitch proxy upstream authentication configured: fastmcp_version=%s "
    "key_length=%d key_sha256_prefix=%s header_present=%s",
    _fastmcp_version(),
    len(api_key),
    _key_fingerprint(api_key),
    "X-Goog-Api-Key" in upstream_headers,
)

upstream_transport = StreamableHttpTransport(
    url=UPSTREAM_URL,
    headers=upstream_headers,
)

# Prefect Horizon entrypoint: main.py:mcp
mcp = create_proxy(upstream_transport, name="Google Stitch MCP Proxy")


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
