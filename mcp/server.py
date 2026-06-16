#!/usr/bin/env python3
"""
AI Property MCP Server
Exposes PropertyAI and KV2025 agents to Claude Desktop.
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ── Paths (dynamic) ───────────────────────────────────────────────────────────
# Packaged plugin: AI_PROPERTY_DATA points at the bundled data dir (${CLAUDE_PLUGIN_ROOT}/data).
# Repo dev mode: no env var → resolve relative to this file (repo root).
ROOT = Path(os.environ["AI_PROPERTY_DATA"]) if os.environ.get("AI_PROPERTY_DATA") else Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source"
AGENTS = ROOT / ".claude" / "agents"
SKILLS = ROOT / ".claude" / "skills"
KB_JSONL = AGENTS / "KV2025_data" / "kb" / "kv_buyer_knowledge_base.jsonl"
KB_SUMMARY = AGENTS / "KV2025_data" / "kb" / "kv_buyer_knowledge_base_summary.md"
KV2025_MD = AGENTS / "KV2025.md"
PROPERTYAI_MD = SKILLS / "PropertyAI" / "SKILL.md"

SOURCE_DOCS = {
    "buying-strategy": SOURCE / "How to Buy and Invest in Property in Malaysia_ A Comprehensive Strategic Guide.md",
    "pre-purchase-checklist": SOURCE / "Strategic Pre-Purchase Checklist for Malaysian Real Estate.md",
    "evaluation-criteria": SOURCE / "How to Evaluate a Property_ Criteria for Investment vs Own Stay in Malaysia.md",
    "investment-vs-ownstay": SOURCE / "Buying for Investment vs. Buying for Own Stay in Malaysia_ The Strategist’s Blueprint.md",
    "location-analysis": SOURCE / "How to Analyse a Property Location in Malaysia Like an Expert.md",
    "research-tools": SOURCE / "How to Research Property Data in Malaysia_ Tools, Sources, and Methods.md",
    "master-scoring-framework": SOURCE / "Property Analysis Master Scoring Framework for Malaysia (2025-2026 Edition).md",
}

# Load API key — project .env first, then env block from Claude Desktop config
load_dotenv(ROOT / ".env")
MAPS_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

app = FastMCP("ai-property")


# ── KB filtering helpers (ported from query_kb.py) ────────────────────────────

VOICE_TYPES = {"reddit_thread", "forum_thread", "qna", "x_thread", "x_community", "fb_group"}


def _normalize(s):
    return str(s).strip().lower() if s else ""


def _field_contains(record, field, needle):
    needle_n = _normalize(needle)
    val = record.get(field)
    if isinstance(val, list):
        return any(needle_n in _normalize(item) for item in val)
    return needle_n in _normalize(val)


def _cluster_of(r):
    segs = set(_normalize(s) for s in (r.get("buyer_segment") or []))
    cns = set(_normalize(c) for c in (r.get("top_concerns") or []))
    schs = set(_normalize(s) for s in (r.get("government_scheme_signals") or []))
    own = _normalize(r.get("own_stay_or_invest", ""))
    emos = set(_normalize(e) for e in (r.get("emotional_signals") or []))
    is_ftb = any("first" in s for s in segs)
    is_inv = "investor" in segs or "investment" in own
    is_family = any("family" in s for s in segs)
    is_single = "single" in segs or "young_single" in [_normalize(l) for l in (r.get("life_stage") or [])]
    is_anxious = any(w in " ".join(emos) for w in ["anxiety", "fear", "confusion", "frustration", "distrust"])
    has_scheme = bool(schs) and any(
        k in s for s in schs
        for k in ("rumawip", "pr1ma", "first home", "subsidised", "mampu", "selangorku", "lppsa")
    )
    is_oversupply_aware = any(
        k in c for c in cns
        for k in ("oversupply", "capital_loss", "aging", "negative", "unsold", "take-up")
    )
    is_affordability = any(
        k in c for c in cns
        for k in ("afford", "downpayment", "loan", "dsr", "price")
    )
    if is_inv and is_oversupply_aware:
        return "C2"
    if is_ftb and has_scheme:
        return "C3"
    if is_ftb and is_anxious:
        return "C1"
    if is_ftb and is_affordability:
        return "C4"
    if is_family:
        return "C5"
    if is_inv:
        return "C6"
    if is_single:
        return "C7"
    return "C8"


def _load_kb():
    records = []
    with open(KB_JSONL) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARN: skipping invalid JSON: {e}", file=sys.stderr)
    return records


# ── Tools ─────────────────────────────────────────────────────────────────────

@app.tool()
def kb_query(
    cluster: Optional[str] = None,
    area: Optional[str] = None,
    scheme: Optional[str] = None,
    segment: Optional[str] = None,
    concern: Optional[str] = None,
    quote_search: Optional[str] = None,
    source_type: Optional[str] = None,
    voices_only: bool = False,
    surveys_only: bool = False,
    output_mode: str = "summaries",
    limit: int = 20,
) -> str:
    """Query the Klang Valley Buyer-Psyche knowledge base (134 records from Reddit,
    Lowyat, X, and REHDA surveys). Use for persona work, ad copy, positioning briefs,
    content strategy, or any task needing grounded KV buyer psychology.

    cluster: C1=Anxious FTB, C2=Skeptical investor, C3=Scheme-dependent FTB,
             C4=Affordability-squeezed FTB, C5=Family upgrader, C6=Yield investor,
             C7=Young single, C8=General
    output_mode: 'summaries' (default), 'quotes' (verbatim voices only), 'full' (complete JSON)
    voices_only: restrict to Reddit/forums/Q&A/X — real buyer voices, no editorial
    surveys_only: restrict to REHDA quantitative surveys only
    """
    records = _load_kb()

    if voices_only:
        records = [r for r in records if r.get("source_type") in VOICE_TYPES]
    if surveys_only:
        records = [r for r in records if r.get("source_type") == "survey"]
    if area:
        records = [r for r in records if _field_contains(r, "klang_valley_areas_mentioned", area)]
    if scheme:
        records = [r for r in records if _field_contains(r, "government_scheme_signals", scheme)]
    if segment:
        records = [r for r in records if _field_contains(r, "buyer_segment", segment)]
    if concern:
        records = [r for r in records if _field_contains(r, "top_concerns", concern)]
    if source_type:
        records = [r for r in records if _normalize(r.get("source_type")) == _normalize(source_type)]
    if cluster:
        records = [r for r in records if _cluster_of(r) == cluster.upper()]
    if quote_search:
        needle = quote_search.lower()
        records = [r for r in records if any(needle in q.lower() for q in (r.get("key_quotes") or []))]

    records = records[:max(1, min(limit, 50))]

    if output_mode == "quotes":
        out = []
        for r in records:
            for q in (r.get("key_quotes") or []):
                out.append(q)
        return json.dumps({"count": len(records), "quotes": out}, ensure_ascii=False)

    if output_mode == "full":
        return json.dumps({"count": len(records), "records": records}, ensure_ascii=False, indent=2)

    # summaries (default)
    summaries = []
    for r in records:
        summaries.append({
            "cluster": _cluster_of(r),
            "source_url": r.get("source_url", ""),
            "source_type": r.get("source_type", ""),
            "areas": r.get("klang_valley_areas_mentioned", []),
            "summary": r.get("summary", ""),
        })
    return json.dumps({"count": len(summaries), "records": summaries}, ensure_ascii=False, indent=2)


@app.tool()
def read_kb_summary() -> str:
    """Read the full KV2025 knowledge base summary — cluster taxonomy, REHDA quantitative
    anchors, segment cross-tabs, and provenance tiers. Call this first when starting any
    KV buyer-psyche task to orient yourself before using kb_query."""
    return KB_SUMMARY.read_text(encoding="utf-8")


@app.tool()
def geocode_address(address: str) -> str:
    """Convert a Malaysian property address into lat/lng coordinates.
    Always call this first before distance_matrix or nearby_places.
    Estimated cost: ~$0.005 per call. Inform the user before calling.

    address: Full property address or building name,
             e.g. 'Pavilion Damansara Heights, Kuala Lumpur'
    """
    if not MAPS_KEY:
        return json.dumps({"error": "GOOGLE_MAPS_API_KEY not configured"})
    resp = httpx.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": address, "key": MAPS_KEY},
        timeout=10,
    )
    data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        return json.dumps({"error": data.get("status", "NO_RESULT"), "address": address})
    result = data["results"][0]
    loc = result["geometry"]["location"]
    return json.dumps({
        "lat": loc["lat"],
        "lng": loc["lng"],
        "formatted_address": result.get("formatted_address", ""),
        "status": "OK",
    })


@app.tool()
def distance_matrix(
    origin_lat: float,
    origin_lng: float,
    destinations: list,
    mode: str = "walking",
) -> str:
    """Calculate walking/driving/transit distance from a property to destinations
    (e.g. MRT stations, schools, malls). Use after geocode_address.
    Estimated cost: ~$0.005 per origin-destination pair. Inform user before calling.

    destinations: list of destination names/addresses, e.g.
                  ['Damansara Damai MRT Station, Malaysia', 'KLCC, Kuala Lumpur']
    mode: 'walking' (default), 'driving', or 'transit'
    """
    if not MAPS_KEY:
        return json.dumps({"error": "GOOGLE_MAPS_API_KEY not configured"})
    resp = httpx.get(
        "https://maps.googleapis.com/maps/api/distancematrix/json",
        params={
            "origins": f"{origin_lat},{origin_lng}",
            "destinations": "|".join(destinations),
            "mode": mode,
            "key": MAPS_KEY,
        },
        timeout=15,
    )
    data = resp.json()
    if data.get("status") != "OK":
        return json.dumps({"error": data.get("status", "FAILED")})
    results = []
    rows = data.get("rows", [])
    dest_addresses = data.get("destination_addresses", [])
    if rows:
        elements = rows[0].get("elements", [])
        for i, elem in enumerate(elements):
            dest_label = destinations[i] if i < len(destinations) else dest_addresses[i] if i < len(dest_addresses) else f"destination_{i}"
            if elem.get("status") == "OK":
                results.append({
                    "destination": dest_label,
                    "distance_m": elem["distance"]["value"],
                    "distance_text": elem["distance"]["text"],
                    "duration_text": elem["duration"]["text"],
                    "mode": mode,
                })
            else:
                results.append({"destination": dest_label, "status": elem.get("status", "UNKNOWN")})
    return json.dumps({"count": len(results), "results": results}, indent=2)


@app.tool()
def nearby_places(
    lat: float,
    lng: float,
    place_type: str,
    radius_m: int = 2000,
    max_results: int = 5,
) -> str:
    """Find nearby amenities around a property using Google Places API (New).
    Use after geocode_address.
    Estimated cost: ~$0.032 per call. Inform user before calling.

    place_type: one of hospital, school, shopping_mall, supermarket, bank,
                subway_station, train_station, park, university
    radius_m: search radius in metres (default 2000, max 5000)
    max_results: number of results to return (default 5, max 10)
    """
    if not MAPS_KEY:
        return json.dumps({"error": "GOOGLE_MAPS_API_KEY not configured"})
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": min(max_results, 10),
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": min(radius_m, 5000),
            }
        },
    }
    resp = httpx.post(
        "https://places.googleapis.com/v1/places:searchNearby",
        json=payload,
        headers={
            "X-Goog-Api-Key": MAPS_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.types",
        },
        timeout=15,
    )
    data = resp.json()
    places = data.get("places", [])
    results = []
    for p in places:
        results.append({
            "name": p.get("displayName", {}).get("text", ""),
            "address": p.get("formattedAddress", ""),
            "types": p.get("types", []),
        })
    return json.dumps({"count": len(results), "place_type": place_type, "results": results}, indent=2)


@app.tool()
def text_search_places(
    query: str,
    lat: float,
    lng: float,
    radius_m: int = 10000,
) -> str:
    """Search for nearby landmarks or employment hubs by free-text query near a location.
    Use to find office parks, business districts, universities within a radius of a property.
    Estimated cost: ~$0.032 per call. Inform user before calling.

    query: e.g. 'office park', 'technology park', 'hospital', 'international school'
    """
    if not MAPS_KEY:
        return json.dumps({"error": "GOOGLE_MAPS_API_KEY not configured"})
    payload = {
        "textQuery": query,
        "maxResultCount": 10,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": min(radius_m, 50000),
            }
        },
    }
    resp = httpx.post(
        "https://places.googleapis.com/v1/places:searchText",
        json=payload,
        headers={
            "X-Goog-Api-Key": MAPS_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress",
        },
        timeout=15,
    )
    data = resp.json()
    places = data.get("places", [])
    results = []
    for p in places:
        results.append({
            "name": p.get("displayName", {}).get("text", ""),
            "address": p.get("formattedAddress", ""),
        })
    return json.dumps({"count": len(results), "query": query, "results": results}, indent=2)


# ── Resources ─────────────────────────────────────────────────────────────────

@app.resource("property://guides/buying-strategy")
def guide_buying_strategy() -> str:
    """How to Buy and Invest in Property in Malaysia — full buying process,
    financing, market timing, investment strategy."""
    return SOURCE_DOCS["buying-strategy"].read_text(encoding="utf-8")


@app.resource("property://guides/pre-purchase-checklist")
def guide_pre_purchase() -> str:
    """Strategic Pre-Purchase Checklist — DSR, CCRIS, hidden costs, financial readiness."""
    return SOURCE_DOCS["pre-purchase-checklist"].read_text(encoding="utf-8")


@app.resource("property://guides/evaluation-criteria")
def guide_evaluation() -> str:
    """How to Evaluate a Property — Sean's 7+1 Filter, 85% rule, red flags, valuation."""
    return SOURCE_DOCS["evaluation-criteria"].read_text(encoding="utf-8")


@app.resource("property://guides/investment-vs-ownstay")
def guide_invest_vs_own() -> str:
    """Investment vs Own Stay — strategic decision framework, hybrid strategy,
    portfolio building, REITs vs direct property."""
    return SOURCE_DOCS["investment-vs-ownstay"].read_text(encoding="utf-8")


@app.resource("property://guides/location-analysis")
def guide_location() -> str:
    """How to Analyse a Property Location — 5 location factors, MRT/LRT thresholds,
    amenities scoring, township maturity, future developments."""
    return SOURCE_DOCS["location-analysis"].read_text(encoding="utf-8")


@app.resource("property://guides/research-tools")
def guide_research() -> str:
    """How to Research Property Data — Brickz, NAPIC, EdgeProp, PropertyGuru
    tools, transacted prices, rental yield calculation."""
    return SOURCE_DOCS["research-tools"].read_text(encoding="utf-8")


@app.resource("property://guides/master-scoring-framework")
def guide_scoring() -> str:
    """Property Analysis Master Scoring Framework — full evaluation across all
    dimensions, investment score, own-stay score, final verdict."""
    return SOURCE_DOCS["master-scoring-framework"].read_text(encoding="utf-8")


@app.resource("property://agents/propertyai")
def agent_propertyai() -> str:
    """Full PropertyAI agent instructions — rules, workflows, output format."""
    return PROPERTYAI_MD.read_text(encoding="utf-8")


@app.resource("property://agents/kv2025")
def agent_kv2025() -> str:
    """Full KV2025 agent instructions — buyer clusters, tone, task types."""
    return KV2025_MD.read_text(encoding="utf-8")


@app.resource("property://kb/summary")
def kb_summary_resource() -> str:
    """KV2025 knowledge base summary — cluster taxonomy, REHDA anchors, cross-tabs."""
    return KB_SUMMARY.read_text(encoding="utf-8")


# ── Prompts ───────────────────────────────────────────────────────────────────

@app.prompt()
def evaluate_property(
    property_name: str,
    intent: str,
    asking_price_rm: str = "",
    address: str = "",
) -> str:
    """Start a full Malaysia property evaluation using the PropertyAI framework.
    Loads agent instructions and sets up the structured evaluation.

    intent: 'investment', 'own_stay', or 'both'
    """
    skill_text = PROPERTYAI_MD.read_text(encoding="utf-8")
    price_line = f"Asking price: RM{asking_price_rm}" if asking_price_rm else "Asking price: not provided"
    address_line = f"Address: {address}" if address else "Address: not provided"
    return f"""{skill_text}

---

## Evaluation Request

Property: {property_name}
Intent: {intent}
{price_line}
{address_line}

Begin the evaluation following your standard output format. Start with financial readiness check (Rule 2) before moving into the scoring sections. Remember to declare API costs (Rule 0) before making any Google Maps or WebSearch calls."""


@app.prompt()
def kv_buyer_strategy(
    task_type: str,
    target_cluster: str = "",
    area: str = "",
    context: str = "",
) -> str:
    """Start a KV2025 buyer-psyche strategy session for persona work, positioning,
    ad copy, content calendars, or scheme guidance.

    task_type: 'persona', 'positioning_brief', 'ad_copy', 'content_calendar',
               'scheme_guidance', or 'buyer_research'
    target_cluster: C1–C8 (optional — omit for cross-cluster work)
    """
    agent_text = KV2025_MD.read_text(encoding="utf-8")
    summary_text = KB_SUMMARY.read_text(encoding="utf-8")
    cluster_line = f"Target cluster: {target_cluster}" if target_cluster else "Target cluster: cross-cluster (use kb_query to identify most relevant)"
    area_line = f"Area focus: {area}" if area else "Area focus: general KV"
    context_line = f"Additional context: {context}" if context else ""
    return f"""{agent_text}

---

## Knowledge Base Summary

{summary_text}

---

## Task Brief

Task type: {task_type}
{cluster_line}
{area_line}
{context_line}

Use the kb_query tool to pull relevant records before generating your output. For persona or ad copy work, use output_mode='quotes' to get verbatim buyer voices. For quantitative claims, set surveys_only=True and cite the REHDA source."""


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(transport="stdio")
