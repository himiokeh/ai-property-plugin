# AI Property 🏠🇲🇾

A Malaysia property assistant for Claude. It adds:

- **Evaluate Property** — buy / wait / walk-away verdict on a specific unit (Sean Tan's 7+1
  Filter, Peter Yong's 85% rule, a master scoring framework).
- **KV Buyer Strategy** — Klang Valley buyer-psyche work: personas, positioning, ad copy,
  content calendars — grounded in a 134-record buyer knowledge base (Reddit / Lowyat / X +
  REHDA surveys).
- **Property Research** — paste a PropertyGuru URL → scrape → Google Maps enrichment → a
  structured JSON report.

It works with **no API keys** for the first two skills. Maps and scraping need free keys
(details below).

---

## Install — pick your app

### A) Claude Desktop (Cowork) — easiest

1. **One-time tools** (open Terminal):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux  (Windows: see note below)
   brew install node                                  # or nodejs.org
   ```
2. Download **`ai-property.plugin`** from this repo (click the file above → Download).
3. In Claude Desktop: **Cowork → Plugins → Add Plugin** → select `ai-property.plugin`.
4. Enter your own Google Maps / Firecrawl keys when asked (or leave blank to skip).

That's it — the plugin is self-contained.

### B) Claude Code — clone & go

1. Install the same one-time tools (`uv` and `node`, as above).
2. Clone and open this repo in Claude Code:
   ```bash
   git clone https://github.com/himiokeh/ai-property-plugin.git
   cd ai-property-plugin
   claude
   ```
3. Tell Claude: **"set this up"**. It reads `CLAUDE.md` and wires everything up — the MCP
   server auto-registers and its dependencies install on first use.
4. (Optional) For maps & scraping, set your keys before launching:
   ```bash
   export GOOGLE_MAPS_API_KEY="your-key"
   export FIRECRAWL_API_KEY="your-key"
   ```

> **Windows:** install uv with `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
> and Node from nodejs.org. Set keys via System Environment Variables.

---

## Getting API keys (both optional, both have free tiers)

| Key | Where | Free tier |
|---|---|---|
| Google Maps | console.cloud.google.com → enable Geocoding API, Distance Matrix API, Places API (New) | generous monthly credit |
| Firecrawl | firecrawl.dev → Dashboard → API Keys | 500 credits/month |

Your keys stay on your own machine. They are **not** included in this repo or the plugin file.

---

## What's in here

| Path | What |
|---|---|
| `ai-property.plugin` | Prebuilt, self-contained plugin for Cowork |
| `.mcp.json` | Project config for Claude Code (auto-loads on open) |
| `.claude/skills/` | The three skills |
| `mcp/server.py` | The MCP server (Google Maps + buyer-KB tools) |
| `data/` | Bundled property guides + buyer knowledge base |
| `CLAUDE.md` | Setup instructions Claude reads automatically |

---

## Requirements

- **uv** — runs the Python server (auto-installs its deps): https://astral.sh/uv
- **Node.js 18+** — runs the Firecrawl scraper (only needed for `property-research`)
