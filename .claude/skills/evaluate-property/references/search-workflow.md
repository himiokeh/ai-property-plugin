# WebSearch Workflow

Query patterns for retrieving live Malaysian property market data. Always use `WebSearch`, then follow up with `WebFetch` on the most relevant URL to extract specific numbers.

---

## 1. Transacted Prices (Brickz)

Use when verifying if asking price is reasonable.

```
brickz [building name] transacted price [year]
```

Examples:
- `brickz Tropicana Gardens transacted price 2024`
- `brickz The Birchley Sri Hartamas transacted price 2025`
- `brickz Mirage Residence KLCC transacted 2024 2025`

Extract: median transacted PSF (RM per sqft) and median transacted price for comparable units.

Fallbacks:
- `[building name] transacted price Malaysia property 2024 2025`
- `[building name] subsale price history Malaysia`

---

## 2. Rental Listings & Comps

Use for the 85% rule, gross rental yield calculation, or rental demand verification.

```
[property name OR area] [unit type] for rent PropertyGuru Malaysia
```

Examples:
- `Tropicana Gardens condo for rent PropertyGuru`
- `Mont Kiara 3 bedroom apartment for rent 2025`
- `Ara Damansara condominium rental listing`

Extract:
- Median monthly rent for comparable units (same area, similar sqft)
- Rental range (low–high)
- Number of active listings (high count = oversupply risk)

---

## 3. NAPIC Overhang Data

Use when checking if a postcode/area has a property glut.

```
NAPIC overhang [state OR area] residential [year]
```

Examples:
- `NAPIC overhang Kuala Lumpur condominium 2024`
- `NAPIC Malaysia residential overhang report 2025`
- `NAPIC Selangor property overhang statistics`

Extract: number of unsold units, percentage overhang, which property types are oversupplied.

---

## 4. EdgeProp Price History & Trend

Use when the user wants to know whether prices are rising, flat, or declining.

```
EdgeProp [area OR building] price trend Malaysia
```

Examples:
- `EdgeProp Bangsar South price trend 2023 2024 2025`
- `EdgeProp Cheras condo price history`
- `EdgeProp Iskandar Puteri residential price trend`

Extract:
- Year-on-year price change (%)
- Current median PSF vs 3 years ago
- Whether the trend is upward, flat, or declining

---

## 5. Developer Track Record

Use for Rule 6 red flag check.

Check for problems first:
```
[developer name] abandoned project Malaysia
[developer name] complaint Malaysia property buyer
[developer name] VP Malaysia       (VP = Vacant Possession delay)
```

Examples:
- `Mammoth Empire abandoned project Malaysia`
- `Country Garden Malaysia complaint 2023 2024`
- `Tropicana Corporation abandoned VP delayed`

Extract: news of abandonment, delays >24 months, insolvency, REHDA complaints, JMB/MC formation issues.

Positive track record:
```
[developer name] completed projects Malaysia list
[developer name] developer reputation review Malaysia
```

---

## 6. Area News & Future Developments

Use to evaluate future infrastructure (capital appreciation drivers) and competing supply (price depressors).

```
[area] development news Malaysia 2025
[area] MRT LRT new station Malaysia
[area] new township master plan
```

Examples:
- `Alam Impian Shah Alam development news 2025`
- `Kepong MRT3 station location Malaysia`
- `Johor Bahru RTS Link property impact 2025`

Extract:
- Upcoming MRT/LRT/BRT stations within 3km
- New highways / interchanges planned
- Major employment anchor (office park, hospital, university, hypermarket)
- New competing supply (large new launches in same postcode)

---

## 7. Rental Yield Benchmarks

Use to calibrate whether a calculated yield is good or bad relative to the area.

```
[area] rental yield 2024 2025 Malaysia property
gross rental yield [area] Malaysia condo
```

Examples:
- `KLCC condo rental yield 2024 2025`
- `Petaling Jaya Section 13 rental yield Malaysia`
- `Johor Bahru Iskandar residential rental yield 2025`

Benchmarks:
- <4% gross = poor for investment
- 4–5% = acceptable
- 5–6% = good
- >6% = excellent (verify if sustainable)

---

## Search Best Practices

1. Always include the current year (2025/2026) in queries to get fresh data.
2. Try 2–3 query variations if the first does not return Brickz/EdgeProp/PropertyGuru.
3. `WebFetch` the actual listing/data page URL to extract specific numbers.
4. Cross-reference at least 2 sources before quoting a price figure.
5. Always present data as "according to [source] as of [date]" — never state transacted prices as absolute fact without attribution.
