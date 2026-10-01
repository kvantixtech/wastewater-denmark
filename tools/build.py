#!/usr/bin/env python3
"""Builds the results from data/raw/ as described in METHOD.md.

  python3 tools/build.py      runs the checks, writes results/summary.md and results/site.json

Exits 1 if a check in METHOD.md fails. Standard library only; same inputs give the same bytes out.
"""
import csv, json, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "results")
COMBINED = ("OV", "OS", "OF", "OK", "Bypass", "UR", "SKYBRUD")
SEPARATE = ("SE", "SF")
DST_TYPES = {"Almene renseanlæg": "plants", "Regnbetinget udledning": "rain", "Industriel udledning": "industry",
             "Spredt bebyggelse ikke tilsluttet kloakering": "scattered"}
DST_MEASURES = {"Spildevand, 1.000 m3": "water", "Kvælstof, ton total-N": "n", "Fosfor, ton total-P": "p", "Organisk stof, ton BI5": "bi5"}
# Punktkilder 2024 (Miljøstyrelsen, NOVANA), national totals for 2024
REPORT_2024 = {"plants": {"water_mio_m3": 810.9, "n_t": 3850, "p_t": 364, "bi5_t": 2505},
               "rain": {"water_mio_m3": 453.1, "n_t": 1476, "p_t": 219, "bi5_t": 4323},
               "combined": {"water_mio_m3": 57.9, "n_t": 764, "p_t": 123, "bi5_t": 2188}}
# Calculation levels (Miljøstyrelsen, DTA for regnbetingede udledninger): stated uncertainty on substance amounts
LEVELS = {"0": "PULS area unit values", "1": "simple mass balance (±135 %)", "2": "uncalibrated hydraulic model (±100 %)",
          "3": "calibrated hydraulic model (±55 %)", "4": "software sensor or flow-based (±45 %)", "5": "measured flow and concentrations (±30 %)"}


def num(x):
    return 0.0 if x in ("", None) else float(x)


def level(text):
    m = re.search(r"(?:niveau|niv\.|nineau)\s*:?\s*(\d)", text or "", re.I)
    return m.group(1) if m else "not stated"


def read_csv(name, delimiter=","):
    with open(os.path.join(RAW, name), encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


def main():
    problems = []
    info = json.load(open(os.path.join(RAW, "dst_vandud_tableinfo.json"), encoding="utf-8"))
    areas = [v["text"] for v in info["variables"][0]["values"]]
    munis = [a for a in areas if a != "Hele landet" and not a.startswith("Region ")]
    years = [int(v["text"]) for v in info["variables"][3]["values"]]
    lower = {m.lower(): m for m in munis}

    def muni(name):
        s = re.sub(r"\s+kommune$", "", name.strip(), flags=re.I)
        s = re.sub(r"regionskommune$", "", s, flags=re.I).strip()
        s = {"københavns": "københavn", "bornholms": "bornholm"}.get(s.lower(), s.lower())
        return lower.get(s)

    # ---- DST VANDUD
    dst = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [None] * len(years))))
    for r in read_csv("dst_vandud.csv", ";"):
        t, m = DST_TYPES.get(r["ANLAEG"]), DST_MEASURES.get(r["UDL"])
        if not t or not m:
            continue
        v = None if r["INDHOLD"].strip() in ("..", "", "-") else float(r["INDHOLD"])
        dst[r["OMRÅDE"]][t][m][years.index(int(r["TID"]))] = v
    nat = dst["Hele landet"]

    # ---- MIM layers, 2024
    rens = read_csv("rens_2024.csv")
    rbu = read_csv("rbu_2024.csv")
    for rows, tag in ((rens, "plant"), (rbu, "outlet")):
        years_in = Counter(r["aar"] for r in rows)
        if list(years_in) != ["2024"]:
            problems.append(f"{tag} layer is not all 2024: {dict(years_in)}")
    sums = lambda rows: {"water_mio_m3": round(sum(num(r["udl_va_sta"]) for r in rows) / 1e6, 1),
                         "n_t": round(sum(num(r["udl_tn_sta"]) for r in rows) / 1e3), "p_t": round(sum(num(r["udl_tp_sta"]) for r in rows) / 1e3),
                         "bi5_t": round(sum(num(r["udl_bi_sta"]) for r in rows) / 1e3)}
    comb = [r for r in rbu if r["bgv_type"] in COMBINED]
    sep = [r for r in rbu if r["bgv_type"] in SEPARATE]
    other = [r for r in rbu if r["bgv_type"] not in COMBINED + SEPARATE]
    if other:
        problems.append(f"{len(other)} outlets with an unknown structure type: {Counter(r['bgv_type'] for r in other)}")
    got = {"plants": sums(rens), "rain": sums(rbu), "combined": sums(comb)}

    # ---- Checks 1 and 2: layers vs DST vs Punktkilder 2024
    i24 = years.index(2024)
    for key in ("plants", "rain"):
        d = {"water_mio_m3": round(nat[key]["water"][i24] / 1e3, 1), "n_t": nat[key]["n"][i24], "p_t": nat[key]["p"][i24], "bi5_t": nat[key]["bi5"][i24]}
        for k, v in REPORT_2024[key].items():
            if got[key][k] != v or round(d[k], 1) != v:
                problems.append(f"check {key} {k}: layer {got[key][k]}, DST {d[k]}, report {v}")
    for k, v in REPORT_2024["combined"].items():
        if got["combined"][k] != v:
            problems.append(f"check combined {k}: layer {got['combined'][k]}, report {v}")

    # ---- Check 3: municipality names
    unmatched = Counter(r["komm_navn"] for r in rens + rbu if not muni(r["komm_navn"]) and r["komm_navn"] != "Miljøstyrelsen")
    if unmatched:
        problems.append(f"unmatched municipality names: {dict(unmatched)}")

    # ---- Calculation levels for combined-sewage overflows
    def level_table(rows):
        t = defaultdict(lambda: {"outlets": 0, "water_m3": 0.0, "n_kg": 0.0})
        for r in rows:
            x = t[level(r["ber_met"])]
            x["outlets"] += 1; x["water_m3"] += num(r["udl_va_sta"]); x["n_kg"] += num(r["udl_tn_sta"])
        return {k: {kk: round(vv) if kk != "outlets" else vv for kk, vv in t[k].items()} for k in sorted(t)}
    lv = level_table(comb)
    meas = sum(lv[k]["outlets"] for k in ("4", "5") if k in lv)
    calc = sum(lv[k]["outlets"] for k in ("0", "1", "2", "3") if k in lv)

    # ---- Per municipality
    per = {}
    for m in munis:
        mr = [r for r in rens if muni(r["komm_navn"]) == m]
        mc = [r for r in comb if muni(r["komm_navn"]) == m]
        ms = [r for r in sep if muni(r["komm_navn"]) == m]
        top = sorted(mc, key=lambda r: (-num(r["udl_va_sta"]), r["pkt_navn"]))[:10]
        per[m] = {
            "dst": {t: {k: dst[m][t][k] for k in ("water", "n", "p", "bi5")} for t in DST_TYPES.values()},
            "plants": [[r["pkt_navn"], r["ejer"] or "", round(num(r["udl_va_sta"])), round(num(r["udl_tn_sta"]) / 1e3, 2), round(num(r["udl_tp_sta"]) / 1e3, 2), r["rens_sta"]]
                       for r in sorted(mr, key=lambda r: (-num(r["udl_va_sta"]), r["pkt_navn"]))],
            "overflows": {"outlets": len(mc), "water_m3": round(sum(num(r["udl_va_sta"]) for r in mc)), "n_t": round(sum(num(r["udl_tn_sta"]) for r in mc) / 1e3, 2),
                          "measured": sum(1 for r in mc if level(r["ber_met"]) in ("4", "5")), "level5": sum(1 for r in mc if level(r["ber_met"]) == "5"),
                          "top": [[r["pkt_navn"], r["ejer"] or "", r["bgv_type"], round(num(r["udl_va_sta"])), round(num(r["udl_tn_sta"]) / 1e3, 3), level(r["ber_met"])] for r in top]},
            "separate": {"outlets": len(ms), "water_m3": round(sum(num(r["udl_va_sta"]) for r in ms))},
        }

    site = {"years": years, "national": {t: {k: nat[t][k] for k in ("water", "n", "p", "bi5")} for t in DST_TYPES.values()},
            "y2024": {"plants": dict(got["plants"], count=len(rens)), "combined": dict(got["combined"], count=len(comb)),
                      "separate": dict(sums(sep), count=len(sep)), "levels_combined": lv, "level_names": LEVELS,
                      "measured_outlets": meas, "calculated_outlets": calc, "level5_outlets": lv.get("5", {}).get("outlets", 0)},
            "munis": per, "manifest": json.load(open(os.path.join(ROOT, "data", "manifest.json"), encoding="utf-8"))["downloaded_at_utc"]}
    os.makedirs(OUT, exist_ok=True)
    json.dump(site, open(os.path.join(OUT, "site.json"), "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    # ---- summary.md
    L = ["# Results", "", "Generated by `tools/build.py`. Do not edit by hand.", "",
         f"Data downloaded {site['manifest']}. Sources in `METHOD.md`.", "", "## Checks", ""]
    L += ["All checks passed." if not problems else "**Checks failed:**"] + [f"- {p}" for p in problems] + [""]
    L += ["## 2024, national", "", "| | Count | Water (million m³) | N (t) | P (t) | BI5 (t) |", "|---|---|---|---|---|---|"]
    for key, label in (("plants", "Treatment plants"), ("combined", "Overflows of combined sewage"), ("separate", "Separate rainwater")):
        x = site["y2024"][key]
        L.append(f"| {label} | {x['count']:,} | {x['water_mio_m3']} | {x['n_t']:,} | {x['p_t']:,} | {x['bi5_t']:,} |")
    L += ["", "## Overflows of combined sewage by calculation level, 2024", "", "| Level | Meaning | Outlets | Water (m³) | N (kg) |", "|---|---|---|---|---|"]
    for k, x in lv.items():
        L.append(f"| {k} | {LEVELS.get(k, '')} | {x['outlets']:,} | {x['water_m3']:,} | {x['n_kg']:,} |")
    L += ["", f"Based on measurement (levels 4–5): {meas:,} of {len(comb):,} outlets. Level 5 alone: {site['y2024']['level5_outlets']:,}.", ""]
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[8:12]))
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
