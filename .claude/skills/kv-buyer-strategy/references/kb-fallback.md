# KB Fallback — When the MCP Server Is Not Connected

If `mcp__ai-property__kb_query` and `mcp__ai-property__read_kb_summary` error out or are unavailable, fall back to reading the KB files that ship inside this plugin directly.

## Locate the files

The plugin bundles two KB files under its own `data/` directory:

- `kv_buyer_knowledge_base.jsonl` — 134 records (one JSON object per line)
- `kv_buyer_knowledge_base_summary.md` — human-readable analysis + cluster taxonomy

Don't assume an absolute path — find them with `Glob`:

```
**/kv_buyer_knowledge_base.jsonl
**/kv_buyer_knowledge_base_summary.md
```

## Load and filter in Python

```python
import glob, json
path = glob.glob("**/kv_buyer_knowledge_base.jsonl", recursive=True)[0]
records = [json.loads(line) for line in open(path) if line.strip()]

# Example: records mentioning an area
hits = [r for r in records
        if any("Bukit Jalil" in str(a) for a in r.get("klang_valley_areas_mentioned", []))]
```

Each record carries `buyer_segment`, `top_concerns`, `government_scheme_signals`,
`klang_valley_areas_mentioned`, `source_type`, `summary`, and `key_quotes` — filter on
whichever fields the task needs. For the cluster taxonomy and REHDA survey anchors,
read `kv_buyer_knowledge_base_summary.md`.
