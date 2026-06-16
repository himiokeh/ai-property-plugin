# Extraction Schema Reference

Canonical JSON shape produced by `property-research`. Treat this as the contract — downstream consumers (`evaluate-property`, your colleague's image-download script, future analytics) depend on these field names.

## Top-level

| Field | Type | Notes |
|---|---|---|
| `source.url` | string | The input PropertyGuru URL |
| `source.scraped_at` | string | ISO 8601 UTC timestamp |
| `source.scraper` | string | `firecrawl` |
| `property` | object | Core listing facts |
| `geocode` | object | `{ lat, lng, formatted_address }` |
| `unit_types` | array | Layout variants offered |
| `facilities` | array of strings | Building amenities |
| `media.gallery_images` | array of strings | Photo / render URLs |
| `media.floor_plan_images` | array of strings | Floor plan URLs |
| `nearby.<bucket>` | array | 7 buckets, each with up to 10 places |

## `property` object

| Field | Type | Notes |
|---|---|---|
| `name` | string | Project name as displayed |
| `developer` | string | Developer entity name |
| `location` | string | Full address text |
| `tenure` | enum | `Freehold` / `Leasehold` / `Unknown` |
| `type` | string | Free-text — Condominium, Service Residence, Landed, etc. |
| `total_units` | integer | 0 if unknown |
| `completion` | string | Year or quarter — `2026`, `Q4 2025` |
| `price_range` | string | As displayed — `RM 600k – RM 1.2m` |
| `description` | string | Project intro / blurb |

## `unit_types[]` item

| Field | Type | Notes |
|---|---|---|
| `name` | string | Type label — `Type A`, `2 BR Standard` |
| `size_sqft` | integer | Built-up area in sqft |
| `bedrooms` | integer | |
| `bathrooms` | integer | |
| `price_from` | string | As displayed — `RM 685,000` |

## `nearby.<bucket>[]` item

Each place entry across all 7 buckets:

| Field | Type | Notes |
|---|---|---|
| `name` | string | Place display name |
| `distance_m` | integer | Walking distance in metres |
| `walk_mins` | integer | Walking duration, rounded to nearest minute |

## Buckets and source `place_type`

| Bucket | `place_type` calls (Places API New) |
|---|---|
| `train` | `transit_station` |
| `schools` | `school` |
| `shopping` | `supermarket`, `convenience_store`, `shopping_mall` (merge + dedupe) |
| `healthcare` | `hospital`, `doctor`, `pharmacy` (merge + dedupe) |
| `food_and_drink` | `restaurant`, `cafe` (merge + dedupe) |
| `parks` | `park` |
| `places_of_worship` | `place_of_worship` |

Default radius: 2000m. Top 10 per bucket after merge.
