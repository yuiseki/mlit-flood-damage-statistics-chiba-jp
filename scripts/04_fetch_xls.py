#!/usr/bin/env python3
"""Download the selected EXCEL files (docs/catalog_selected.tsv, selection == selected), one at a time, 2 s apart.

    uv run python scripts/04_fetch_xls.py [--date YYYY-MM-DD] [--tstat 000001222080 ...]

URL: https://www.e-stat.go.jp/stat-search/file-download?statInfId=<ID>&fileKind=0 (the plain download link of the site).
Each file is saved unchanged as raw/<date>/xls/<statInfId>.<ext>; raw/<date>/MANIFEST.json keeps the sha256, the fetch time and
the headers (Last-Modified, Content-Disposition, Content-Type). A 401/403/429 stops the run (estat.Blocked). Resumable.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import estat

ROOT = Path(__file__).parents[1]


def ext_of(body: bytes) -> str:
    if body[:2] == b"PK":
        return "xlsx"
    if body[:8] == bytes.fromhex("D0CF11E0A1B11AE1"):
        return "xls"
    return "bin"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-10-31")
    ap.add_argument("--tstat", nargs="*")
    a = ap.parse_args()
    out = ROOT / "raw" / a.date
    (out / "xls").mkdir(parents=True, exist_ok=True)
    mf_path = out / "MANIFEST.json"
    mf = json.loads(mf_path.read_text()) if mf_path.exists() else {}
    rows = [r for r in csv.DictReader((ROOT / "docs" / "catalog_selected.tsv").open(encoding="utf-8"), delimiter="\t")
            if r["selection"] == "selected" and (not a.tstat or r["tstat"] in a.tstat)]
    print(len(rows), "files to consider", flush=True)
    for i, r in enumerate(rows, 1):
        sid = r["statInfId"]
        if sid in mf and mf[sid].get("file") and (out / mf[sid]["file"]).exists():
            continue
        url = f"{estat.BASE}/stat-search/file-download?statInfId={sid}&fileKind=0"
        status, headers, body = estat.fetch(url)
        if status != 200:
            mf[sid] = {"url": url, "status": status, "fetched_at": estat.now(), "file": None}
            print(f"[{i}/{len(rows)}] {sid} HTTP {status}", flush=True)
            mf_path.write_text(json.dumps(mf, ensure_ascii=False, indent=1) + "\n")
            continue
        name = f"{sid}.{ext_of(body)}"
        (out / "xls" / name).write_bytes(body)
        mf[sid] = {"url": url, "status": status, "fetched_at": estat.now(), "file": f"xls/{name}", "bytes": len(body),
                   "sha256": estat.sha256_bytes(body), "last_modified": headers.get("Last-Modified"),
                   "content_disposition": headers.get("Content-Disposition"), "content_type": headers.get("Content-Type"),
                   "title": r["title"], "survey_year_label": r["survey_year_label"], "tstat": r["tstat"]}
        mf_path.write_text(json.dumps(mf, ensure_ascii=False, indent=1) + "\n")
        print(f"[{i}/{len(rows)}] {sid} {name} {len(body)} bytes {headers.get('Last-Modified')}", flush=True)


if __name__ == "__main__":
    main()
