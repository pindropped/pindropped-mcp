"""MCP server exposing PinDropped tools over stdio (default) or streamable HTTP."""
from __future__ import annotations

import sys
from typing import Any

from mcp.types import ToolAnnotations

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server  # type: ignore
    from mcp.server.fastmcp.exceptions import ToolError  # type: ignore
import functools

from . import client as pd

INSTRUCTIONS = (
    "PinDropped (https://pindropped.app) is a neighborhood map bulletin board, born on Capitol Hill in "
    "Washington, DC, usable anywhere. Use search_pins to find local events, notices, lost pets, free stuff, "
    "and small businesses near a place. Use create_pin ONLY on behalf of a real user who has approved the "
    "exact pin (location, title, details, category, plan). Free pins last 12 hours; paid pins are $1/day; "
    "Permanent pins are $20/month and need the user to complete Stripe checkout."
)

mcp = _Server("pindropped", instructions=INSTRUCTIONS)


def _friendly(fn):
    """Surface PinDroppedError messages to the model instead of a generic tool error."""
    @functools.wraps(fn)
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except pd.PinDroppedError as e:
            raise ToolError(str(e)) from e
    return wrapper



@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
@_friendly
def search_pins(
    lat: float | None = None,
    lng: float | None = None,
    radius_m: float = 1000,
    bbox: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Find live pins on the PinDropped map.

    Give either lat+lng (+ radius_m, default 1000 m, max 50000; results sorted by distance) or
    bbox="minLng,minLat,maxLng,maxLat". Optional category filter: one of
    event, sale, free, lost_found, help, housing, business, notice, fun, other.
    Each result includes title, body, category, link, expires_at, and a shareable url.
    """
    return pd.search_pins(bbox=bbox, lat=lat, lng=lng, radius_m=radius_m, category=category, limit=limit)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
@_friendly
def get_pin(id: str) -> dict[str, Any]:
    """Get one PinDropped pin by its id (e.g. '2f2187f85a7c'). Returns full details plus its share url."""
    return pd.get_pin(id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
@_friendly
def pin_url(id: str) -> str:
    """Return the public, shareable page URL for a pin id (https://pindropped.app/p/{id}). Pages have link-preview cards."""
    return pd.pin_url(id)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
    )
)
@_friendly
def create_pin(
    lat: float,
    lng: float,
    title: str,
    user_confirmed: bool,
    details: str = "",
    category: str = "other",
    link: str = "",
    plan: str = "free",
    days: int | None = None,
) -> dict[str, Any]:
    """Post a PUBLIC pin to the PinDropped map on behalf of the user.

    REQUIRES THE USER'S EXPLICIT CONFIRMATION. Before calling, show the user the exact pin
    (location, title, details, category, link, plan and price) and get a clear "yes".
    Set user_confirmed=true only after that. Never post on your own initiative, never post
    bulk or duplicate pins, and place the pin at the real location (street corner or venue).

    - title: max 80 chars (tip for events: start with the date, e.g. "Sat 10/25: Pie contest")
    - details: max 500 chars
    - category: event, sale, free, lost_found, help, housing, business, notice (Announcement), fun, other
    - link: optional full https:// URL
    - plan: "free" (up 12 hours, $0), "daily" ($1/day; set days 1-10000), or "monthly" (Permanent, $20/month)
    Paid plans return a Stripe checkout_url; the pin goes live only after the user pays there.
    Returns the pin url (free) or checkout_url (paid).
    """
    if not user_confirmed:
        raise pd.PinDroppedError(
            "Not posted: show the user the exact pin and get explicit approval, then call again with user_confirmed=true."
        )
    return pd.create_pin(
        lat=lat, lng=lng, title=title, details=details, category=category, link=link, plan=plan, days=days
    )


def main() -> None:
    transport = "stdio"
    if "--http" in sys.argv:
        transport = "streamable-http"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
