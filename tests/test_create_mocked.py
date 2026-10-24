"""create_pin is tested ONLY against a mocked HTTP transport. It never touches the real site."""
import httpx
import pytest
import respx

from pindropped_mcp import client as pd
from pindropped_mcp import server


def _form(request: httpx.Request) -> dict:
    body = request.content.decode()
    out = {}
    for part in body.split("--")[1:]:
        if 'name="' in part:
            name = part.split('name="')[1].split('"')[0]
            out[name] = part.split("\r\n\r\n", 1)[1].rsplit("\r\n", 1)[0]
    return out


@respx.mock
def test_free_pin_posts_days_0():
    route = respx.post("https://pindropped.app/api/pins").mock(
        return_value=httpx.Response(200, json={"url": "/p/abc123"})
    )
    res = pd.create_pin(lat=38.9, lng=-76.99, title="Sat 10/25: Yard sale", details="8-noon", category="For sale")
    sent = _form(route.calls[0].request)
    assert sent["days"] == "0" and sent["category"] == "sale" and sent["body"] == "8-noon"
    assert "multipart/form-data" in route.calls[0].request.headers["content-type"]
    assert res["url"] == "https://pindropped.app/p/abc123"
    assert "checkout_url" not in res


@respx.mock
def test_monthly_returns_checkout():
    route = respx.post("https://pindropped.app/api/pins").mock(
        return_value=httpx.Response(200, json={"checkout_url": "https://checkout.stripe.com/c/pay/cs_test_x"})
    )
    res = pd.create_pin(lat=38.9, lng=-76.99, title="Joe's Deli", category="business", plan="monthly")
    assert _form(route.calls[0].request)["days"] == "-1"
    assert res["checkout_url"].startswith("https://checkout.stripe.com")
    assert "pays" in res["next_step"]


@respx.mock
def test_daily_sends_days():
    route = respx.post("https://pindropped.app/api/pins").mock(
        return_value=httpx.Response(200, json={"checkout_url": "https://checkout.stripe.com/x"})
    )
    pd.create_pin(lat=38.9, lng=-76.99, title="Lost cat", category="lost_found", plan="daily", days=3)
    assert _form(route.calls[0].request)["days"] == "3"


@respx.mock
def test_server_error_surfaces_detail():
    respx.post("https://pindropped.app/api/pins").mock(return_value=httpx.Response(400, json={"detail": "Title too long"}))
    with pytest.raises(pd.PinDroppedError, match="Title too long"):
        pd.create_pin(lat=1, lng=1, title="x")


@pytest.mark.parametrize(
    "kwargs,msg",
    [
        ({"title": "x" * 81}, "max 80"),
        ({"title": "ok", "details": "y" * 501}, "max 500"),
        ({"title": "ok", "link": "http://insecure.example"}, "https"),
        ({"title": "ok", "category": "spam"}, "unknown category"),
        ({"title": "ok", "plan": "daily"}, "days"),
        ({"title": "ok", "lat": 99}, "out of range"),
    ],
)
@respx.mock
def test_validation_never_calls_api(kwargs, msg):
    route = respx.post("https://pindropped.app/api/pins")
    args = {"lat": 38.9, "lng": -76.99, **kwargs}
    with pytest.raises(pd.PinDroppedError, match=msg):
        pd.create_pin(**args)
    assert not route.called


@respx.mock
def test_tool_refuses_without_confirmation():
    route = respx.post("https://pindropped.app/api/pins")
    with pytest.raises(Exception, match="user_confirmed"):
        server.create_pin(lat=38.9, lng=-76.99, title="Hi", user_confirmed=False)
    assert not route.called


def test_pin_url():
    assert pd.pin_url("abc") == "https://pindropped.app/p/abc"
    with pytest.raises(pd.PinDroppedError):
        pd.pin_url("../etc")
