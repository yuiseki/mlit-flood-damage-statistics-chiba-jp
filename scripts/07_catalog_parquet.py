#!/usr/bin/env python3
"""data/parquet/catalog.parquet: every file of every survey year of the e-Stat list (docs/catalog_selected.tsv) with what was done to it.

    uv run python scripts/07_catalog_parquet.py [--date YYYY-MM-DD]
"""

import argparse
import csv
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import sys

sys.path.insert(0, str(Path(__file__).parent))
import extract

ROOT = Path(__file__).parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-10-31")
    a = ap.parse_args()
    mf = json.loads((ROOT / "raw" / a.date / "MANIFEST.json").read_text())
    tabs = pq.read_table(ROOT / "data" / "parquet" / "tables.parquet").to_pylist()
    chiba = {}
    for t in tabs:
        c = chiba.setdefault(t["table_id"], {"sheets": 0, "rows": 0})
        c["sheets"] += 1
        c["rows"] += t["chiba_rows"]
    out = []
    for r in csv.DictReader((ROOT / "docs" / "catalog_selected.tsv").open(encoding="utf-8"), delimiter="\t"):
        sid = r["statInfId"]
        m = mf.get(sid, {})
        c = chiba.get(sid)
        out.append({
            "survey_year": extract.survey_year_of(r["survey_year_label"]), "survey_year_label": r["survey_year_label"].split("（")[0],
            "tstat": r["tstat"], "tclass1": r["tclass1"], "group": r["group"] or None, "title": r["title"], "table_no": extract.table_no_of(r["title"]),
            "statInfId": sid, "survey_ym": r["survey_ym"] or None, "published": r["published"] or None, "formats": r["formats"],
            "selection": r["selection"], "fetched": bool(m.get("file")), "fetched_at": m.get("fetched_at"), "source_file": f"raw/{a.date}/{m['file']}" if m.get("file") else None,
            "bytes": m.get("bytes"), "sha256": m.get("sha256"), "last_modified_header": m.get("last_modified"),
            "content_disposition": m.get("content_disposition"), "sheets_read": c["sheets"] if c else None, "chiba_rows": c["rows"] if c else None,
        })  # fmt: skip
    schema = pa.schema([(k, pa.int16() if k == "survey_year" else pa.int64() if k in ("bytes", "sheets_read", "chiba_rows") else pa.bool_() if k == "fetched" else pa.string()) for k in out[0]])
    out.sort(key=lambda r: (r["survey_year"], r["tclass1"], r["statInfId"]))
    pq.write_table(pa.Table.from_pylist(out, schema=schema), ROOT / "data" / "parquet" / "catalog.parquet", compression="zstd")
    print(len(out), "files in the catalog;", sum(1 for r in out if r["fetched"]), "fetched")


if __name__ == "__main__":
    main()
