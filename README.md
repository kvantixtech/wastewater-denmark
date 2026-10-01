# Where Denmark's wastewater goes

Treatment plants, sewer overflows and rainwater outlets, municipality by municipality: how much water, nitrogen, phosphorus and organic matter they discharge, as reported to the national database PULS. It also shows how much of what is reported about overflows is measured rather than calculated.

**2024 in one table** (from [`results/summary.md`](results/summary.md)):

| | Count | Water (million m³) | N (t) | P (t) |
|---|---|---|---|---|
| Treatment plants | 633 | 810.9 | 3,850 | 364 |
| Overflows of combined sewage | 4,195 | 57.9 | 764 | 123 |
| Separate rainwater outlets | 16,445 | 395.2 | 711 | 96 |

Of the 4,195 overflows of combined sewage, 36 report volumes based on measured flow and concentrations (calculation level 5). Another 517 use a flow-based or software-sensor estimate (level 4). The other 3,635 are calculated from models or standard values (levels 0–3).

Part of the Kvantix [Data Playground](https://kvantix.tech/playground/). The rules are in [`METHOD.md`](METHOD.md). `tools/fetch.py` downloads the open data, with SHA-256 for every file in [`data/manifest.json`](data/manifest.json). `tools/build.py` checks the data against the national totals and writes `results/`. CI recomputes everything on every push.

## Sources

- Danmarks Statistik, table VANDUD (spildevandsudledning), free reuse with source.
- Miljøministeriet, MiljøGIS WFS, layers from the basis analysis for the water plans 2027–2033 (`vp4basis2026`), 2024 data.
- Miljøstyrelsen, *Punktkilder 2024* (NOVANA), for the national check.

All three are based on PULS (Danmarks Miljøportal), where utilities, municipalities and Miljøstyrelsen report the discharges. Kvantix is not affiliated with any of them, and none of them endorses this summary.

Code: MIT. Compiled tables: CC BY 4.0, credit "Kvantix wastewater-denmark" and the sources above.
