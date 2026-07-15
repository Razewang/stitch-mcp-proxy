"""Prefect Horizon entrypoint for a secured Google Stitch MCP proxy."""

from __future__ import annotations

import os

from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server import create_proxy

UPSTREAM_URL = "https://stitch.googleapis.com/mcp"
API_KEY_ENV = "STITCH_API_KEY"


def _required_env(name: str) -> str:
    """Return a required environment variable or fail with a clear message."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            "Configure it as a secret in the deployment environment."
        )
    return value


# Clients connect only to this proxy. The Google API key is injected server-side
# and is never required in the downstream client's MCP configuration.
upstream_transport = StreamableHttpTransport(
    url=UPSTREAM_URL,
    headers={"X-Goog-Api-Key": _required_env(API_KEY_ENV)},
)

# Prefect Horizon entrypoint: main.py:mcp
mcp = create_proxy(upstream_transport, name="Google Stitch MCP Proxy")


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
