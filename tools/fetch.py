#!/usr/bin/env python3
"""Downloads the open data described in METHOD.md into data/raw/ and writes data/manifest.json (SHA-256 per file).
Standard library only. Run on GitHub Actions (.github/workflows/fetch.yml)."""
import csv, hashlib, io, json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
UA = "kvantixtech/wastewater-denmark (+https://github.com/kvantixtech/wastewater-denmark)"
WFS = "https://wfs2-miljoegis.mim.dk/ows"
LAYERS = [("vp4basis2026:vp4_ba_26_punkt_rens_saml", "rens_2024"), ("vp4basis2026:vp4_ba_26_punkt_rbu_saml", "rbu_2024")]


def get(url, data=None, hdr=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(hdr or {})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=300) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(20 * (attempt + 1))


def main():
    os.makedirs(RAW, exist_ok=True)
    man = {"downloaded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}

    def save(name, b, src):
        open(os.path.join(RAW, name), "wb").write(b)
        man["files"][name] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b), "source": src}

    js = lambda q: json.dumps(q).encode()
    hj = {"Content-Type": "application/json"}
    q = {"table": "VANDUD", "format": "BULK", "lang": "da", "variables": [{"code": c, "values": ["*"]} for c in ("OMRÅDE", "UDL", "ANLAEG", "Tid")]}
    save("dst_vandud.csv", get("https://api.statbank.dk/v1/data", js(q), hj), "Danmarks Statistik, api.statbank.dk/v1/data, table VANDUD")
    save("dst_vandud_tableinfo.json", get("https://api.statbank.dk/v1/tableinfo", js({"table": "VANDUD", "lang": "da", "format": "JSON"}), hj),
         "Danmarks Statistik, api.statbank.dk/v1/tableinfo, table VANDUD")
    for layer, tag in LAYERS:
        save(tag + "_schema.xsd", get(WFS + "?" + urllib.parse.urlencode({"service": "WFS", "version": "2.0.0", "request": "DescribeFeatureType", "typeNames": layer})),
             "Miljøministeriet MiljøGIS WFS, " + layer)
        rows, start = [], 0
        while True:
            u = WFS + "?" + urllib.parse.urlencode({"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": layer,
                                                   "outputFormat": "application/json", "count": "5000", "startIndex": str(start), "sortBy": "pkt_id"})
            feats = json.loads(get(u)).get("features", [])
            rows += [f["properties"] for f in feats]
            if len(feats) < 5000:
                break
            start += 5000
        cols = sorted({k for r in rows for k in r})
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
        save(tag + ".csv", buf.getvalue().encode("utf-8"), "Miljøministeriet MiljøGIS WFS, " + layer + " (attributes, no geometry)")
        man["files"][tag + ".csv"]["rows"] = len(rows)
    json.dump(man, open(os.path.join(ROOT, "data", "manifest.json"), "w"), indent=1, ensure_ascii=False)
    print("downloaded", ", ".join(f"{k} ({v['bytes']} bytes)" for k, v in man["files"].items()))


if __name__ == "__main__":
    main()
