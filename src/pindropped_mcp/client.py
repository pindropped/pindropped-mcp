"""Thin, dependency-light client for the public PinDropped API (https://pindropped.app/openapi.json)."""
from __future__ import annotations

import math
import os
from typing import Any
from urllib.parse import urlparse

import httpx

BASE_URL = os.environ.get("PINDROPPED_BASE_URL", "https://pindropped.app").rstrip("/")
USER_AGENT = "pindropped-mcp/0.1.0 (+https://pindropped.app/agents)"

# value -> label, exactly as the site's post form (<select name="category">) uses them.
CATEGORIES: dict[str, str] = {
    "event": "Event",
    "sale": "For sale",
    "free": "Free",
    "lost_found": "Lost & found",
    "help": "Help & services",
    "housing": "Housing",
    "business": "Small business",
    "notice": "Announcement",
    "fun": "Just for fun",
    "other": "Other",
}
TITLE_MAX = 80
DETAILS_MAX = 500
MAX_DAYS = 365
EARTH_R = 6371000.0


class PinDroppedError(Exception):
    pass


def pin_url(pin_id: str) -> str:
    pin_id = str(pin_id).strip()
    if not pin_id or "/" in pin_id or "?" in pin_id:
        raise PinDroppedError("invalid pin id")
    return f"{BASE_URL}/p/{pin_id}"


def normalize_category(cat: str | None) -> str | None:
    if cat is None or cat == "":
        return None
    c = cat.strip()
    if c in CATEGORIES:
        return c
    for value, label in CATEGORIES.items():  # accept labels too ("Lost & found", "Announcement")
        if c.lower() == label.lower():
            return value
    raise PinDroppedError(f"unknown category {cat!r}; use one of {sorted(CATEGORIES)}")


def bbox_around(lat: float, lng: float, radius_m: float) -> tuple[float, float, float, float]:
    dlat = math.degrees(radius_m / EARTH_R)
    dlng = math.degrees(radius_m / (EARTH_R * max(math.cos(math.radians(lat)), 1e-6)))
    return (max(lng - dlng, -180), max(lat - dlat, -90), min(lng + dlng, 180), min(lat + dlat, 90))


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def _client(client: httpx.Client | None) -> httpx.Client:
    return client or httpx.Client(base_url=BASE_URL, timeout=20, headers={"User-Agent": USER_AGENT})


def _check(resp: httpx.Response) -> Any:
    try:
        data = resp.json()
    except ValueError:
        data = {"detail": resp.text[:200]}
    if resp.status_code >= 400:
        detail = data.get("detail") if isinstance(data, dict) else data
        raise PinDroppedError(f"HTTP {resp.status_code}: {detail}")
    return data


def _decorate(p: dict[str, Any]) -> dict[str, Any]:
    p = dict(p)
    p["url"] = pin_url(p["id"])
    return p


def search_pins(
    *,
    bbox: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_m: float = 1000,
    category: str | None = None,
    limit: int = 50,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    cat = normalize_category(category)
    if bbox:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            raise PinDroppedError("bbox must be minLng,minLat,maxLng,maxLat")
        box = tuple(parts)
    elif lat is not None and lng is not None:
        if radius_m <= 0 or radius_m > 50000:
            raise PinDroppedError("radius_m must be between 1 and 50000")
        box = bbox_around(lat, lng, radius_m)
    else:
        raise PinDroppedError("pass either bbox or lat+lng")
    c = _client(client)
    resp = c.get("/api/pins", params={"bbox": ",".join(f"{v:.6f}" for v in box), "limit": 300})
    pins = _check(resp)
    out = []
    for p in pins:
        if cat and p.get("category") != cat:
            continue
        if lat is not None and lng is not None and not bbox:
            d = distance_m(lat, lng, p["lat"], p["lng"])
            if d > radius_m:
                continue
            p = {**p, "distance_m": round(d)}
        out.append(_decorate(p))
    if lat is not None and lng is not None and not bbox:
        out.sort(key=lambda p: p["distance_m"])
    return out[: max(1, min(limit, 300))]


def get_pin(pin_id: str, client: httpx.Client | None = None) -> dict[str, Any]:
    pin_url(pin_id)  # validates
    return _decorate(_check(_client(client).get(f"/api/pins/{pin_id}")))


def plan_to_days(plan: str, days: int | None) -> int:
    """free -> 0 (12h), daily -> N paid days ($1/day), monthly -> -1 ($20/mo Permanent)."""
    plan = (plan or "free").lower()
    if plan == "free":
        return 0
    if plan == "monthly":
        return -1
    if plan == "daily":
        if days is None or not (1 <= int(days) <= MAX_DAYS):
            raise PinDroppedError(f"daily plan needs days between 1 and {MAX_DAYS}")
        return int(days)
    raise PinDroppedError("plan must be 'free', 'daily', or 'monthly'")


def validate_new_pin(lat: float, lng: float, title: str, details: str, category: str, link: str) -> str:
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise PinDroppedError("lat/lng out of range")
    if not title or not title.strip():
        raise PinDroppedError("title is required")
    if len(title) > TITLE_MAX:
        raise PinDroppedError(f"title is {len(title)} chars; max {TITLE_MAX}")
    if len(details or "") > DETAILS_MAX:
        raise PinDroppedError(f"details is {len(details)} chars; max {DETAILS_MAX}")
    if link:
        u = urlparse(link)
        if u.scheme != "https" or not u.netloc:
            raise PinDroppedError("link must be a full https:// URL")
    cat = normalize_category(category) or "other"
    return cat


def create_pin(
    *,
    lat: float,
    lng: float,
    title: str,
    details: str = "",
    category: str = "other",
    link: str = "",
    plan: str = "free",
    days: int | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    cat = validate_new_pin(lat, lng, title, details, category, link)
    api_days = plan_to_days(plan, days)
    form = {
        "lat": f"{lat:.6f}",
        "lng": f"{lng:.6f}",
        "title": title.strip(),
        "body": (details or "").strip(),
        "link": link or "",
        "category": cat,
        "days": str(api_days),
    }
    # The site posts multipart/form-data; send fields as multipart parts.
    files = {k: (None, v) for k, v in form.items()}
    data = _check(_client(client).post("/api/pins", files=files))
    checkout = data.get("checkout_url") if isinstance(data, dict) else None
    url = data.get("url") if isinstance(data, dict) else None
    result: dict[str, Any] = {"raw": data, "plan": plan, "days_sent": api_days}
    if checkout:
        result["checkout_url"] = checkout
        result["next_step"] = (
            "Paid plan: the pin goes live only after the user pays. Give the user this Stripe "
            "checkout link to open and pay themselves. Never enter card details for them without consent."
        )
    if url:
        result["url"] = url if url.startswith("http") else f"{BASE_URL}{url}"
    return result
