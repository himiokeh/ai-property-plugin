---
name: property-research
description: End-to-end Malaysian property research workflow. Auto-trigger when the user pastes a PropertyGuru URL (propertyguru.com.my/property-listing/project/... or .../listing/...) or says "research this property", "scrape this listing", "pull data on this project", "build a property report", "property research". Scrapes the listing via Firecrawl (bypasses Cloudflare), enriches with Google Maps (geocode + 7 nearby-place categories + walking distances), and writes a single structured JSON report to the project's research/ folder. Use for due diligence prep, batch research, or feeding downstream evaluation. Distinct from evaluate-property — this skill collects raw data; evaluate-property turns data into a buy/wait/walk-away verdict.
---

# Property Research — PropertyGuru → Google Maps → JSON Report

End-to-end research pipeline for a single Malaysian property listing. Take a PropertyGuru URL, return a structured JSON report with property facts, unit types, facilities, image URLs (split gallery vs floor plans), and 7 categories of nearby places with walking distances.

This skill is data-collection, not analysis. After it runs, hand the JSON to `evaluate-property` for a buy/wait/walk verdict, or to `kv-buyer-strategy` for persona/positioning work.

---

## Tool Stack

| Tool | Purpose | Cost |
|---|---|---|
| `mcp__plugin_ai-property_firecrawl__firecrawl_extract` | Structured extraction from PropertyGuru with a JSON schema. Bypasses Cloudflare. | Firecrawl plan — usually 1–5 credits per page |
| `mcp__plugin_ai-property_firecrawl__firecrawl_scrape` | Fallback if `firecrawl_extract` misses fields — returns raw HTML/markdown. | Firecrawl plan |
| `mcp__plugin_ai-property_ai-property__geocode_address` | Address → lat/lng | $0.005/call |
| `mcp__plugin_ai-property_ai-property__nearby_places` | Places API New nearby search | $0.032/call |
| `mcp__plugin_ai-property_ai-property__distance_matrix` | Walking distance/time per origin–destination element | $0.005 per element |
| `Write` | Persist JSON report | free |

---

## Rule 0 — Declare Cost Before Running

Before running the workflow, show the user a cost table and wait for confirmation:

```
Property Research workflow — cost estimate:
─────────────────────────────────────────────
Firecrawl extract     1 call    ~1–5 credits
geocode_address       1 call    ~$0.005
nearby_places         7 calls   ~$0.224
distance_matrix       7 calls   ~$0.350  (up to 70 elements)
─────────────────────────────────────────────
Estimated Maps cost: ~$0.58 (~RM2.60)
Firecrawl: deducted from your monthly plan credits
Proceed? (yes / no)
```

If the user says "trim cost", offer:
- Drop `distance_matrix` (saves $0.35) — places returned without walk-time
- Reduce nearby radius from 2000m to 1500m
- Drop the 3 lowest-priority categories (parks, places_of_worship, food_and_drink)

Do not call any tool until the user confirms.

---

## Workflow

### Step 1 — Validate Input

Input: a PropertyGuru URL.

- Project pages: `https://www.propertyguru.com.my/property-listing/project/...`
- Listing pages: `https://www.propertyguru.com.my/property-listing/...`

If the URL is from another portal (EdgeProp, iProperty), tell the user this skill is currently PropertyGuru-only and offer to scrape with `firecrawl_scrape` (raw markdown, no schema) as a degraded path.

Derive a slug for the output filename from the URL's last path segment (lowercase, replace non-alphanumerics with hyphens, trim). Example: `m-aurora-for-sale-by-mah-sing-group-berhad-501128317` → `m-aurora.json` (use the leading recognisable token; otherwise the full slug).

### Step 2 — Firecrawl Structured Extraction

Call `firecrawl_extract` with this schema:

```json
{
  "type": "object",
  "properties": {
    "property": {
      "type": "object",
      "properties": {
        "name":         { "type": "string" },
        "developer":    { "type": "string" },
        "location":     { "type": "string", "description": "Full address as displayed on the page, including city and state" },
        "tenure":       { "type": "string", "enum": ["Freehold", "Leasehold", "Unknown"] },
        "type":         { "type": "string", "description": "e.g. Condominium, Service Residence, Landed" },
        "total_units":  { "type": "integer" },
        "completion":   { "type": "string", "description": "Year or quarter, e.g. 2026 or Q4 2025" },
        "price_range":  { "type": "string" },
        "description":  { "type": "string" }
      }
    },
    "unit_types": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name":        { "type": "string" },
          "size_sqft":   { "type": "integer" },
          "bedrooms":    { "type": "integer" },
          "bathrooms":   { "type": "integer" },
          "price_from":  { "type": "string" }
        }
      }
    },
    "facilities": {
      "type": "array",
      "items": { "type": "string" }
    },
    "media": {
      "type": "object",
      "properties": {
        "gallery_images": {
          "type": "array",
          "items": { "type": "string", "description": "Direct image URL for property photos / renders" }
        },
        "floor_plan_images": {
          "type": "array",
          "items": { "type": "string", "description": "Direct image URL for floor plan / unit layout images. Identify by URL pattern (contains 'floor', 'layout', 'type-a', 'type-b' etc.) or by surrounding label text 'floor plan' / 'unit layout'" }
        }
      }
    }
  }
}
```

Firecrawl returns the populated object. If `media.floor_plan_images` is empty but `media.gallery_images` has obvious floor-plan URLs (URL contains `floor`, `layout`, `unit-type`), reclassify them post-hoc.

### Step 3 — Geocode

Construct the geocoding query as `<property.name>, <property.location>`. Example: `M Aurora, Jalan Klang Lama, Old Klang Road, Kuala Lumpur`.

```
geocode_address(address="<property.name>, <property.location>")
```

If `status` is not `OK`, retry with a shortened query: building name + state only.

### Step 4 — Nearby Places (7 Categories)

For each category, call `nearby_places(lat, lng, place_type=..., radius_meters=2000, max_results=10)`. Some categories require multiple calls then merge + dedupe by name + address (or place_id if returned).

| Output bucket | place_type calls | Merge strategy |
|---|---|---|
| `train` | `transit_station` | direct |
| `schools` | `school` | direct |
| `shopping` | `supermarket`, `convenience_store`, `shopping_mall` | merge, dedupe |
| `healthcare` | `hospital`, `doctor`, `pharmacy` | merge, dedupe |
| `food_and_drink` | `restaurant`, `cafe` | merge, dedupe |
| `parks` | `park` | direct |
| `places_of_worship` | `place_of_worship` | direct |

After merge, keep top 10 per bucket (initial order preserved — Places API returns by relevance/proximity).

### Step 5 — Walking Distances

For each bucket, call `distance_matrix` once with all destinations passed as a list of "<place_name>, Malaysia" strings:

```
distance_matrix(
    origin_lat=<lat>,
    origin_lng=<lng>,
    destinations=["<name1>, Malaysia", "<name2>, Malaysia", ...],
    mode="walking"
)
```

Parse `rows[0].elements[i].distance.value` (metres) and `rows[0].elements[i].duration.value` (seconds → divide by 60, round). Sort the bucket ascending by `distance_m`.

If an element returns `status: ZERO_RESULTS`, drop that place from the bucket. Don't fail the run.

### Step 6 — Assemble JSON

Final shape (must match exactly — downstream consumers depend on this):

```json
{
  "source": {
    "url": "<input URL>",
    "scraped_at": "<ISO 8601 UTC timestamp>",
    "scraper": "firecrawl"
  },
  "property": {
    "name": "",
    "developer": "",
    "location": "",
    "tenure": "",
    "type": "",
    "total_units": 0,
    "completion": "",
    "price_range": "",
    "description": ""
  },
  "geocode": {
    "lat": 0.0,
    "lng": 0.0,
    "formatted_address": ""
  },
  "unit_types": [
    { "name": "", "size_sqft": 0, "bedrooms": 0, "bathrooms": 0, "price_from": "" }
  ],
  "facilities": [],
  "media": {
    "gallery_images": [],
    "floor_plan_images": []
  },
  "nearby": {
    "train":             [{ "name": "", "distance_m": 0, "walk_mins": 0 }],
    "schools":           [{ "name": "", "distance_m": 0, "walk_mins": 0 }],
    "shopping":          [{ "name": "", "distance_m": 0, "walk_mins": 0 }],
    "healthcare":        [{ "name": "", "distance_m": 0, "walk_mins": 0 }],
    "food_and_drink":    [{ "name": "", "distance_m": 0, "walk_mins": 0 }],
    "parks":             [{ "name": "", "distance_m": 0, "walk_mins": 0 }],
    "places_of_worship": [{ "name": "", "distance_m": 0, "walk_mins": 0 }]
  }
}
```

### Step 7 — Persist

Write the JSON to a `research/<slug>.json` file in the current working folder:

```
research/<slug>.json
```

Create the `research/` folder if it does not exist. Use the `Write` tool. Pretty-print with 2-space indent.

After writing, return a one-paragraph summary to the user with:
- Property name, developer, location
- Number of unit types, facilities, gallery images, floor plans
- Nearest train station and walking time (the headline locational fact)
- The output file path as a `computer://` link
- A prompt: "Want me to run `evaluate-property` on this now?"

---

## Image Classification — Detailed Heuristics

If Firecrawl's extract step doesn't cleanly split gallery vs floor plan, post-process:

A URL belongs in `floor_plan_images` if ANY of:
- URL path contains `floor-plan`, `floorplan`, `layout`, `unit-type`, `type-[a-z]`, `siteplan`
- File name contains `fp`, `floorplan`, `layout`
- Image is rendered next to text "floor plan", "unit layout", "siteplan", "layout plan"
- Image dimensions (if known) suggest a vertical/portrait diagram

Otherwise → `gallery_images`.

If you're uncertain and Firecrawl's HTML output is available, do a quick `firecrawl_scrape` with `formats=["html"]` and re-classify based on DOM context.

---

## Error Handling

- **Firecrawl returns 403/blocked** — retry once with `formats=["markdown"]` and a slightly different `waitFor` (e.g. 3000ms). If it still fails, tell the user the listing might be paywalled or geo-blocked and offer to fall back to a manual URL the user provides.
- **Geocoding ZERO_RESULTS** — try (1) building name + state, (2) just the area name. If still nothing, write the JSON without `geocode` and note the failure in the summary.
- **Places API zero results in a category** — leave the bucket as `[]`. Don't fail the run.
- **`research/` folder not writable** — fall back to the session outputs folder, tell the user where the file landed.

---

## What This Skill Does NOT Do

- Does not download images. The `floor_plan_images[]` and `gallery_images[]` arrays are URL lists for downstream consumers (your colleague's download script). Hand them the JSON and they run a simple loop.
- Does not score the property. That's `evaluate-property`'s job.
- Does not infer buyer-psyche fit. That's `kv-buyer-strategy`'s job.
- Does not handle EdgeProp / iProperty / new launch microsites. PropertyGuru only for now.
