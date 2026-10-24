"""Manual end-to-end check: spawn the server over stdio and call read-only tools."""
import asyncio, json, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "pindropped_mcp.server"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("tools:", [t.name for t in tools.tools])
            res = await s.call_tool("search_pins", {"lat": 38.889, "lng": -77.0, "radius_m": 2000, "category": "event", "limit": 3})
            data = res.structured_content if getattr(res, "structured_content", None) is not None else getattr(res, "structuredContent", None)
            text = res.content[0].text if res.content else ""
            print("search_pins isError:", res.is_error if hasattr(res,"is_error") else res.isError)
            print("search_pins first:", text[:300])
            pid = json.loads(text)["id"] if text.strip().startswith("{") else None
            if pid:
                g = await s.call_tool("get_pin", {"id": pid})
                print("get_pin:", g.content[0].text[:200])
            u = await s.call_tool("pin_url", {"id": "abc"}); print("pin_url:", u.content[0].text)
            c = await s.call_tool("create_pin", {"lat": 38.9, "lng": -77, "title": "x", "user_confirmed": False})
            print("create_pin unconfirmed ->", c.content[0].text[:160])
asyncio.run(main())
