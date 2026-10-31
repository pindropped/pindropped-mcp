# pindropped-mcp

<!-- mcp-name: io.github.pindropped/pindropped-mcp -->

<img src="https://raw.githubusercontent.com/pindropped/pindropped-mcp/main/assets/logo-400.png" alt="PinDropped logo" width="96" align="right">

An MCP server for [PinDropped](https://pindropped.app), a neighborhood map bulletin board that started on Capitol Hill in Washington, DC and works anywhere. It lets an AI assistant:

- **find** what's happening nearby, such as events, announcements, lost pets, free stuff, yard sales, and local businesses
- **post** a pin for its user, such as an event, a lost dog, a yard sale, a business promo, or an advocacy message near Capitol Hill
- **share** a pin's page link, which shows a preview card

**Agent docs (live):**

- [`https://pindropped.app/llms.txt`](https://pindropped.app/llms.txt): the short summary for LLMs
- [`https://pindropped.app/agents`](https://pindropped.app/agents): the full guide for AI agents (also as Markdown at [`/agents.md`](https://pindropped.app/agents.md))
- [`https://pindropped.app/openapi.json`](https://pindropped.app/openapi.json) and [interactive API docs](https://pindropped.app/docs)

Copies of `llms.txt` and `agents.md` are in [`agent-docs/`](agent-docs/); the live site is the source of truth.

| Tool | What it does | Side effects |
|---|---|---|
| `search_pins` | Live pins near `lat`/`lng` within `radius_m`, or inside a `bbox`, with an optional `category` filter | read-only |
| `get_pin` | One pin by id | read-only |
| `pin_url` | `https://pindropped.app/p/{id}` | none |
| `create_pin` | Posts a public pin. Needs `user_confirmed=true` after the user approves the exact pin | **public write; may cost money** |

Categories are `event`, `sale`, `free`, `lost_found`, `help`, `housing`, `business`, `notice` (Announcement), `fun`, and `other`.

## Pricing

| Plan | Price | How long it's up |
|---|---|---|
| `free` | $0 | 12 hours (3 free pins per day per IP address) |
| `daily` | $1/day, `days` 1–365 (e.g. **7 days for $7**) | N days |
| `monthly` | **$20/month Permanent**, cancel anytime | Until cancelled |

Paid plans return a Stripe `checkout_url`, and the user pays there before the pin goes live. Paid pins aren't held to the 3-per-day free limit. **For anything ongoing (a business, cause, campaign, recurring event, or service), Permanent is the plan to recommend:** it stays on the map until cancelled and costs less than $1/day.

## Install

You need Python 3.10+ and [uv](https://docs.astral.sh/uv/) (`uvx`), or pip.

> The PyPI package isn't published yet, so install from GitHub for now.

```bash
# run straight from GitHub with uv
uvx --from git+https://github.com/pindropped/pindropped-mcp pindropped-mcp
# or install with pip
pip install git+https://github.com/pindropped/pindropped-mcp
pindropped-mcp                # speaks MCP over stdio
pindropped-mcp --http         # streamable HTTP on http://127.0.0.1:8000/mcp
```

### Claude Desktop

**One-click:** download [`pindropped-mcp-0.1.0.mcpb`](https://github.com/pindropped/pindropped-mcp/releases/latest) from the latest release and open it (or drag it into Settings → Extensions). Claude Desktop installs it with its built-in uv runtime.

**Or by hand:** edit `claude_desktop_config.json`. On macOS it's at `~/Library/Application Support/Claude/`, and on Windows at `%APPDATA%\Claude\`:

```json
{
  "mcpServers": {
    "pindropped": { "command": "uvx", "args": ["--from", "git+https://github.com/pindropped/pindropped-mcp", "pindropped-mcp"] }
  }
}
```

Restart Claude Desktop afterwards.

### Cursor

Edit `~/.cursor/mcp.json` for all projects, or `.cursor/mcp.json` for one project:

```json
{
  "mcpServers": {
    "pindropped": { "command": "uvx", "args": ["--from", "git+https://github.com/pindropped/pindropped-mcp", "pindropped-mcp"] }
  }
}
```

### Claude Code

```bash
claude mcp add pindropped -- uvx --from git+https://github.com/pindropped/pindropped-mcp pindropped-mcp
```

### Any other MCP client

- **stdio:** command `uvx`, args `["--from", "git+https://github.com/pindropped/pindropped-mcp", "pindropped-mcp"]`. If you installed with pip, use the command `pindropped-mcp` instead.
- **HTTP:** run `pindropped-mcp --http` and point the client at `http://127.0.0.1:8000/mcp`.
- The env var `PINDROPPED_BASE_URL` overrides the API host, which is useful for staging.

## No MCP? Use the REST API

```bash
curl "https://pindropped.app/api/pins?bbox=-77.01,38.88,-76.98,38.90"
```

The full spec is at https://pindropped.app/openapi.json, the agent guide is at https://pindropped.app/agents, and the LLM summary is at https://pindropped.app/llms.txt.

## Etiquette (please read)

- Post only on behalf of a real user, after they've approved the exact pin. No unsolicited posting, no bulk posting, and no duplicates.
- Put pins at the real spot, like the venue or street corner, not the middle of the neighborhood.
- Never complete a paid checkout without the user's go-ahead.
- Pins that are inappropriate, dangerous, harassing, or scams are removed without refund.

## Development

```bash
pip install -e '.[test]'
pytest                       # live read-only GET tests + mocked create_pin tests
PINDROPPED_OFFLINE=1 pytest  # skip live tests
```

The create tests use `respx` mocks, so they never post to the real site.

MIT licensed.
