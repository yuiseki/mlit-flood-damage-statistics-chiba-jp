#!/usr/bin/env python3
"""Extract the Chiba rows of every fetched Excel sheet into the long table and the table catalog (Parquet, zstd).

    uv run python scripts/05_extract.py [--date YYYY-MM-DD]

Writes data/parquet/chiba_long.parquet (one record per cell of a Chiba row), data/parquet/tables.parquet (one record per sheet
read: what was found, how many Chiba rows) and docs/05_extract.log.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent))
import extract

ROOT = Path(__file__).parents[1]

LONG_SCHEMA = pa.schema([
    ("survey_year", pa.int16()), ("survey_year_label", pa.string()), ("table_id", pa.string()), ("table_no", pa.string()),
    ("table_title", pa.string()), ("table_family", pa.string()), ("sheet_title", pa.string()), ("pref_label", pa.string()),
    ("area_code", pa.string()), ("area_name", pa.string()), ("level", pa.string()), ("row_class", pa.string()),
    ("measure", pa.string()), ("value", pa.float64()), ("unit", pa.string()), ("symbol", pa.string()), ("note", pa.string()),
    ("source_statInfId", pa.string()), ("source_file", pa.string()), ("source_sheet", pa.string()), ("source_cell", pa.string()),
    ("source_row", pa.int32()), ("source_col", pa.string()), ("header_cells", pa.string()),
])  # fmt: skip
TABLES_SCHEMA = pa.schema([
    ("survey_year", pa.int16()), ("survey_year_label", pa.string()), ("table_id", pa.string()), ("table_no", pa.string()),
    ("table_title", pa.string()), ("table_family", pa.string()), ("published", pa.string()), ("source_file", pa.string()),
    ("source_sha256", pa.string()), ("fetched_at", pa.string()), ("source_sheet", pa.string()), ("sheet_title", pa.string()),
    ("unit_note", pa.string()), ("key_cols", pa.string()), ("data_cols", pa.string()), ("ignored_label_cols", pa.string()),
    ("first_data_row", pa.int32()), ("sheet_rows", pa.int32()), ("chiba_rows", pa.int32()), ("inherited_rows", pa.int32()), ("ditto_rows", pa.int32()), ("orphan_rows", pa.int32()), ("tree_form", pa.bool_()),
    ("records", pa.int32()), ("footnotes", pa.string()), ("reader_note", pa.string()),
])  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-10-31")
    a = ap.parse_args()
    raw = ROOT / "raw" / a.date
    mf = json.loads((raw / "MANIFEST.json").read_text())
    cat = {r["statInfId"]: r for r in csv.DictReader((ROOT / "docs" / "catalog_selected.tsv").open(encoding="utf-8"), delimiter="\t")}
    longs, tables = [], []
    for sid, v in sorted(mf.items(), key=lambda kv: (cat[kv[0]]["tstat"], kv[0])):
        if not v.get("file"):
            continue
        c = cat[sid]
        year = extract.survey_year_of(c["survey_year_label"])
        meta = {"survey_year": year, "survey_year_label": c["survey_year_label"].split("（")[0], "table_id": sid,
                "table_no": extract.table_no_of(c["title"]), "table_title": c["title"], "table_family": extract.family_of(c["title"]),
                "source_statInfId": sid, "source_file": f"raw/{a.date}/{v['file']}"}  # fmt: skip
        state = extract.State()
        for g in extract.in_reading_order(extract.open_grids(raw / v["file"])):
            recs, d = extract.extract_grid(g, {}, state)
            for r in recs:
                rr = {**meta, **r}
                rr["source_sheet"] = rr.pop("sheet")
                rr["source_col"] = rr.pop("col")
                longs.append(rr)
            tables.append({**{k: meta[k] for k in ("survey_year", "survey_year_label", "table_id", "table_no", "table_title", "table_family")},
                           "published": c["published"], "source_file": meta["source_file"], "source_sha256": v["sha256"],
                           "fetched_at": v["fetched_at"], "source_sheet": d["sheet"], "sheet_title": d["sheet_title"],
                           "unit_note": d["unit_note"], "key_cols": ",".join(d["key_cols"]), "data_cols": ",".join(d["data_cols"]),
                           "ignored_label_cols": ",".join(d["ignored_label_cols"]), "first_data_row": d["first_data_row"],
                           "sheet_rows": d["nrows"], "chiba_rows": d["chiba_rows"], "inherited_rows": d["inherited_rows"], "ditto_rows": d["ditto_rows"], "orphan_rows": d["orphan_rows"], "tree_form": d["tree_form"],
                           "records": len(recs), "footnotes": json.dumps(d["footnotes"], ensure_ascii=False) if d["footnotes"] else None,
                           "reader_note": d["note"]})  # fmt: skip
        print(sid, c["survey_year_label"][:8], c["title"][:30], "->", sum(1 for t in tables if t["table_id"] == sid), "sheets", flush=True)
    out = ROOT / "data" / "parquet"
    out.mkdir(parents=True, exist_ok=True)
    longs.sort(key=lambda r: (r["survey_year"], r["table_id"], r["source_sheet"], r["source_row"], extract.col_index(r["source_col"])))
    pq.write_table(pa.Table.from_pylist(longs, schema=LONG_SCHEMA), out / "chiba_long.parquet", compression="zstd")
    tables.sort(key=lambda r: (r["survey_year"], r["table_id"], r["source_sheet"]))
    pq.write_table(pa.Table.from_pylist(tables, schema=TABLES_SCHEMA), out / "tables.parquet", compression="zstd")
    print(len(longs), "records;", len(tables), "sheets")


if __name__ == "__main__":
    main()
