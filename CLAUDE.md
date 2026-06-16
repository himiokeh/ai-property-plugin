# AI Property — Setup & Usage (read this first)

This repo is a **Malaysia property assistant**. It adds two MCP servers and three skills
to Claude: property evaluation, Klang Valley buyer-psyche strategy, and an end-to-end
property-research scraper.

If a user has just opened this repo and asks you to "set it up", "install it", or "get it
working", follow the **Setup procedure** below. Do not skip the prerequisite checks.

---

## Setup procedure (run these steps)

### 1. Check prerequisites
Run these and report what's missing:
```bash
uv --version || echo "MISSING: uv"
node --version || echo "MISSING: node"
```
- If **uv** is missing: prefer Homebrew on macOS — `brew install uv` — because it avoids the
  "Apple cannot verify" Gatekeeper warning that the raw install script can trigger. On Windows
  use `winget install astral-sh.uv`. Only fall back to `curl -LsSf https://astral.sh/uv/install.sh | sh`
  if Homebrew/winget isn't available, and warn the user they may see a Gatekeeper prompt they can
  approve under System Settings → Privacy & Security. After installing, tell the user to restart
  their terminal / Claude Code so uv is on PATH.
- If **node** is missing: `brew install node` (macOS) or Node 18+ from https://nodejs.org.
  Only the `property-research` (Firecrawl) feature needs it.

### 2. The MCP servers auto-register
This repo ships a project-level `.mcp.json` that Claude Code loads automatically when the
folder is opened. The `ai-property` server runs via `uv run` — on first use, uv installs its
Python dependencies automatically (one-time, ~30s). No manual server setup needed.

If the `ai-property` MCP tools are not visible, ask the user to approve the project's MCP
servers when Claude Code prompts, or re-open the folder.

### 3. API keys (optional — only for maps & scraping)
The two **offline** skills (`evaluate-property`, `kv-buyer-strategy`) work with **no keys** —
they use the property guides and 134-record buyer KB bundled in `data/`.

Maps tools and `property-research` need keys. If the user wants those, have them set the keys
as environment variables before launching Claude Code (the `.mcp.json` reads them):
```bash
export GOOGLE_MAPS_API_KEY="their-key"   # console.cloud.google.com (Geocoding, Distance Matrix, Places New)
export FIRECRAWL_API_KEY="their-key"     # firecrawl.dev — free tier 500 credits/month
```
On Windows, set them via System Environment Variables, then restart Claude Code.
If the user doesn't want maps/scraping, skip this — everything else still works.

### 4. Verify
Confirm setup by calling the `mcp__ai-property__read_kb_summary` tool (free, needs no key).
If it returns the KB summary, the server is working. Report success to the user.

---

## What the user can do once set up

- **"Evaluate this property: <name/URL/price>"** → uses the `evaluate-property` skill
  (Sean Tan 7+1 Filter, 85% rule, master scoring). Maps tools enrich it if a key is set.
- **"Help me with buyer strategy / personas / ad copy for <Klang Valley area>"** → uses
  `kv-buyer-strategy`, grounded in the bundled buyer KB (Reddit/Lowyat/X + REHDA surveys).
- **"Research this PropertyGuru listing: <URL>"** → uses `property-research` (needs Firecrawl
  + Google Maps keys); writes a JSON report to `research/<slug>.json`.

The skills live in `.claude/skills/` and are auto-available while this folder is open.

---

## Using this in Claude Desktop (Cowork) instead

If the user is on Claude Desktop, not Claude Code, they don't need this repo's setup. Tell
them to download **`ai-property.plugin`** from this repo and install it via
**Cowork → Plugins → Add Plugin**, then enter their own API keys when prompted. That file is
fully self-contained.
