# Method: where Denmark's wastewater goes

Written after a first look at the data, which only checked that the open layers add up to the national report, and before any page or ranking was built. Changes are listed in `CHANGELOG.md`, with the reason, before they take effect.

## Question

How much wastewater, nitrogen, phosphorus and organic matter do Danish treatment plants, sewer overflows and rainwater outlets discharge, municipality by municipality? And how much of what is reported about overflows is measured rather than calculated?

This is a description of published data, not a test, and nothing is scored. Kvantix does not judge any utility or municipality.

## Sources

All figures come from data that the utilities, municipalities and Miljøstyrelsen report to PULS, the national point-source database at Danmarks Miljøportal. PULS itself requires a login, so the same data is taken from two open publications of it.

| Source | What | Years | Access |
|---|---|---|---|
| **Danmarks Statistik, table VANDUD** ("Spildevandsudledning") | Water (1,000 m³), total nitrogen, total phosphorus and organic matter (BI5) in tonnes, by municipality and source type | 2010–2024 | `api.statbank.dk`, free reuse with source |
| **Miljøministeriet, MiljøGIS WFS**, layers `vp4basis2026:vp4_ba_26_punkt_rens_saml` (treatment plants) and `vp4basis2026:vp4_ba_26_punkt_rbu_saml` (rain-dependent outlets) | One row per plant or outlet: owner, municipality, type, discharged water (m³) and N, P, BI5, COD (kg), and for outlets the calculation method | 2024 | `wfs2-miljoegis.mim.dk`, no fees or access constraints stated |
| **Miljøstyrelsen, Punktkilder 2024** (NOVANA) | National totals, used as a check | 2024 | PDF report |

Every download is saved unchanged in `data/raw/` with its SHA-256 in `data/manifest.json`.

## Definitions

- **Treatment plants:** DST type "Almene renseanlæg", and every row of the plant layer.
- **Rain-dependent discharges:** DST type "Regnbetinget udledning", and every row of the outlet layer. They are split by structure type (`bgv_type`, PULS code list):
  - **Overflows of combined sewage** (rainwater mixed with sewage): OV, OS, OF, OK (overflow structures with or without basins), Bypass (bypass at a treatment plant), UR (untreated wastewater) and SKYBRUD (cloudburst).
  - **Separate rainwater:** SE and SF (rainwater from separate systems, with or without a detention basin).
- **Calculation level** of an outlet: the first digit after "Niveau" in the free-text field `ber_met`. Miljøstyrelsen's technical instruction for rain-dependent discharges defines:
  - 0: PULS area unit values
  - 1: simple mass balance (uncertainty about 135 %)
  - 2: uncalibrated hydraulic model (100 %)
  - 3: calibrated hydraulic model (55 %)
  - 4: software sensor or flow-based estimate (45 %)
  - 5: measurement of flow and concentrations (30 %)

  Levels 4–5 are reported here as "based on measurement" and levels 0–3 as "calculated". An empty or unreadable field is reported as "not stated".
- **Municipality:** DST's own names. Names in the layers are matched to them after removing "kommune" and changing case ("Københavns Kommune" → København, "Bornholms Regionskommune" → Bornholm). Outlets registered under Miljøstyrelsen rather than a municipality count in the national totals only.
- **Units on the page:** water in m³ (or million m³), substances in tonnes (layer values are kg and are divided by 1,000).

## Checks that must pass before anything is shown

1. The 2024 sums of the plant layer must equal the national figures in DST VANDUD and in Punktkilder 2024 (water, N, P and BI5), each to the reported precision.
2. The 2024 sums of the outlet layer must do the same. The combined-sewage share must equal the report's figures for overflows from combined sewers.
3. Every municipality name in the layers must match a DST name, apart from rows registered under Miljøstyrelsen.

If a check fails, nothing is published until the cause is found and written in `CHANGELOG.md`.

## What this can't show

- **Reported is not observed.** Most outlet figures are calculated from rainfall, catchment area and models. The calculation level is shown next to them.
- **One year per outlet.** The outlet and plant layers cover 2024. Earlier years are available only as municipal totals (DST).
- **Uneven reporting.** The free-text method field is filled in differently by different utilities. The level is read from the text as written, not corrected.
- **Impact on the environment.** The same discharge matters differently in a small stream and in the open sea. That is not assessed.
