# Google Maps Workflow

Primary path is the `ai-property` MCP server. The fallback path (raw `WebFetch`/`curl`) is documented at the bottom for cases where the MCP server is not connected.

---

## Step 1 — Geocode the Address

Convert a property address to lat/lng. Required before distance_matrix or nearby_places.

**MCP tool:** `mcp__ai-property__geocode_address`

```
geocode_address(address="Pavilion Damansara Heights, Kuala Lumpur")
```

Returns `{ lat, lng, formatted_address, status }`. Use `lat` and `lng` for downstream calls.

---

## Step 2 — Walking Distance to MRT/LRT/KTM

Use Distance Matrix to measure walking distance from the property to 2–3 closest known transit stations.

**MCP tool:** `mcp__ai-property__distance_matrix`

```
distance_matrix(
    origin_lat=3.1478,
    origin_lng=101.6953,
    destinations=["Damansara Damai MRT Station, Malaysia", "Surian MRT Station, Malaysia"],
    mode="walking"
)
```

### MRT/LRT Proximity Scoring (Location Score component)

| Walking distance | Score | Label |
|---|---|---|
| < 500m | Excellent | TOD premium zone |
| 500m – 1km | Good | Walkable |
| 1km – 2km | Acceptable | Short ride/e-hailing |
| > 2km | Weak | Transit-dependent penalty |

---

## Step 3 — Nearby Amenities

Find amenities within a radius using Places API (New).

**MCP tool:** `mcp__ai-property__nearby_places`

```
nearby_places(
    lat=3.1579,
    lng=101.7116,
    place_type="hospital",
    radius_meters=3000,
    max_results=5
)
```

**Types and recommended radii:**

| Amenity | place_type | Radius |
|---|---|---|
| Hospital / clinic | `hospital` | 3000 |
| School | `school` | 2000 |
| Shopping mall | `shopping_mall` | 3000 |
| Supermarket | `supermarket` | 1500 |
| Bank | `bank` | 1500 |

---

## Step 4 — Employment Hub Proximity

Use a free-text search for office parks / business districts within 10km.

**MCP tool:** `mcp__ai-property__text_search_places`

```
text_search_places(
    query="office park OR business district",
    lat=3.1478,
    lng=101.6953,
    radius_meters=10000
)
```

Common KL employment hubs to check proximity to:
- KL City Centre (KLCC)
- Bangsar South / KL Eco City
- Petaling Jaya Old Town / SS2
- Subang Jaya / Empire Damansara
- Mont Kiara / Sri Hartamas
- Cyberjaya / Putrajaya
- Bukit Bintang / Pavilion area
- Setia Alam / Shah Alam

---

## Amenity Scoring (Location Score, 30% weight)

After retrieving Places data, score the amenity layer:

| Criterion | Points |
|---|---|
| Hospital/clinic within 3km | +3 |
| International or national school within 2km | +3 |
| Shopping mall (anchor tenant) within 3km | +3 |
| Supermarket within 1.5km | +2 |
| MRT/LRT/KTM within 1km | +5 |
| Highway on-ramp within 2km | +4 |
| Employment hub within 10km | +3 |
| Multiple employment hubs within 10km | +2 bonus |

Maximum amenity sub-score: 25 points (cap at 20 for scoring purposes).

---

## Error Handling

- If a tool errors with "API key invalid": ask the user to check the Google Maps API key they entered in the plugin's config in Cowork (Plugins > ai-property > configure).
- If geocode returns zero results: try a shorter form of the address (building name + state only).
- If nearby_places returns zero results: widen the radius by 50% and retry once.

---

## Fallback — When the MCP Server Is Not Connected

If `mcp__ai-property__*` tools error out or are unavailable, fall back to raw HTTP. Ask the user for their Google Maps API key (the one set in the plugin's Cowork config) first.

**Geocoding (WebFetch GET):**
```
https://maps.googleapis.com/maps/api/geocode/json?address={ENCODED}&key={KEY}
```
Extract `results[0].geometry.location` → `{ lat, lng }`.

**Distance Matrix (WebFetch GET):**
```
https://maps.googleapis.com/maps/api/distancematrix/json?origins={LAT},{LNG}&destinations={DEST}|{DEST}&mode=walking&key={KEY}
```
Extract `rows[0].elements[i].distance.value` (metres).

**Places API (New) Nearby (Bash + curl POST):**
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Goog-Api-Key: {KEY}" \
  -H "X-Goog-FieldMask: places.displayName,places.formattedAddress" \
  -d '{"includedTypes":["{TYPE}"],"maxResultCount":5,"locationRestriction":{"circle":{"center":{"latitude":{LAT},"longitude":{LNG}},"radius":{M}}}}' \
  "https://places.googleapis.com/v1/places:searchNearby"
```

**Text Search (WebFetch GET):**
```
https://maps.googleapis.com/maps/api/place/textsearch/json?query={Q}&location={LAT},{LNG}&radius=10000&key={KEY}
```
