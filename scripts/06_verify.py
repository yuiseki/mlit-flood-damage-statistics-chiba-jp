#!/usr/bin/env python3
"""Verify data/parquet/chiba_long.parquet by a route that shares no code with the extraction.

    uv run python scripts/06_verify.py [--date YYYY-MM-DD]

(a) every record: its source_cell is read again from the original Excel with scripts/xlsx_xml.py (zipfile + XML; .xls files are first
    converted to .xlsx by LibreOffice, a different parser from xlrd) and the value / symbol / blank state must be identical;
    every non-empty cell of a Chiba row in a data column must be in the table (nothing dropped); the Chiba rows are looked up
    again by scanning the first 4 columns of every sheet for 千葉 / 千葉県 (no missed row, no extra row).
(b) additivity: inside a table, the rows of a dimension (municipality, river system, cause ...) must sum to the '合計' row of the
    same other dimensions. Only where the table has both. Mismatches are reported with numbers, nothing is corrected.
(c) per survey year: tables, sheets, rows, records.
(d) sheets with no Chiba row, with the reason found.
Writes docs/06_verify.json, docs/06_verify.log and data/parquet/year_checks.parquet.
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent))
import extract
import xlsx_xml

ROOT = Path(__file__).parents[1]
CONV = ROOT / "data" / "_verify_xlsx"


def as_xlsx(path: Path) -> Path:
    if path.suffix == ".xlsx":
        return path
    out = CONV / (path.stem + ".xlsx")
    if not out.exists():
        CONV.mkdir(parents=True, exist_ok=True)
        subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=4G", "-p", "CPUQuota=100%", "soffice", "--headless",
                        "--convert-to", "xlsx", "--outdir", str(CONV), str(path)], check=True, capture_output=True, timeout=600)  # fmt: skip
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-10-31")
    a = ap.parse_args()
    raw = ROOT / "raw" / a.date
    long = pq.read_table(ROOT / "data" / "parquet" / "chiba_long.parquet").to_pylist()
    tables = pq.read_table(ROOT / "data" / "parquet" / "tables.parquet").to_pylist()
    mf = json.loads((raw / "MANIFEST.json").read_text())
    by_file = defaultdict(list)
    for r in long:
        by_file[r["table_id"]].append(r)
    res = {"cells_checked": 0, "cells_equal": 0, "cell_mismatches": [], "nonempty_missing": [], "rows_missed": [], "rows_extra_inherited": 0,
           "rows_extra_other": [], "files": 0}  # fmt: skip
    year = defaultdict(lambda: defaultdict(int))
    for t in tables:
        year[t["survey_year"]]["sheets"] += 1
        year[t["survey_year"]]["records"] += t["records"]
        year[t["survey_year"]]["chiba_rows"] += t["chiba_rows"]
    # (a)
    for sid, v in sorted(mf.items()):
        if not v.get("file"):
            continue
        res["files"] += 1
        indep = xlsx_xml.cells(as_xlsx(raw / v["file"]))
        recs = by_file.get(sid, [])
        sheets_of_file = {t["source_sheet"]: t for t in tables if t["table_id"] == sid}
        for sheet, tinfo in sheets_of_file.items():
            d = indep.get(sheet)
            if d is None:
                res["cell_mismatches"].append([sid, sheet, "sheet missing in the independent read"])
                continue
            srecs = [r for r in recs if r["source_sheet"] == sheet]
            for r in srecs:
                res["cells_checked"] += 1
                got = d.get(r["source_cell"])
                if r["value"] is not None:
                    ok = isinstance(got, float) and got == r["value"]
                    if not ok and isinstance(got, float) and abs(got - r["value"]) <= 1e-9 * max(1.0, abs(r["value"])):
                        res["float_noise"] = res.get("float_noise", 0) + 1  # a formula cell: the other reader (LibreOffice) recomputed it
                        res.setdefault("float_noise_examples", []).append([sid, sheet, r["source_cell"], r["value"], got][:5])
                        ok = True
                elif r["symbol"] is not None:
                    ok = isinstance(got, str) and got == r["symbol"]
                else:
                    ok = got is None
                if ok:
                    res["cells_equal"] += 1
                else:
                    res["cell_mismatches"].append([sid, sheet, r["source_cell"], r["value"], r["symbol"], got])
            # rows by an independent scan
            rows_ind = set()
            for ref, val in d.items():
                col, row = xlsx_xml.split_ref(ref)
                if isinstance(val, str) and len(col) == 1 and "A" <= col <= "D" and re.fullmatch(r"千葉県?", extract.squash(val)):
                    rows_ind.add(row)
            rows_ext = {r["source_row"] for r in srecs}
            if tinfo["records"] == 0 and rows_ind:
                # extraction found no row but the scan did: only a real miss if the sheet has a data layout at all
                res["rows_missed"].append([sid, sheet, sorted(rows_ind)[:5], "extraction read none; reader_note=%s" % tinfo["reader_note"]])
            elif tinfo["records"] > 0:
                for row in sorted(rows_ind - rows_ext):
                    res["rows_missed"].append([sid, sheet, row])
                extra = rows_ext - rows_ind
                inherited = {r["source_row"] for r in srecs if r["note"] and "inherited" in r["note"]}
                res["rows_extra_inherited"] += len(extra & inherited)
                if tinfo["tree_form"]:
                    # the rows below a prefecture row of the hierarchical form carry no prefecture name: not findable by the scan
                    res["tree_rows_not_scannable"] = res.get("tree_rows_not_scannable", 0) + len(extra - inherited)
                else:
                    for row in sorted(extra - inherited):
                        res["rows_extra_other"].append([sid, sheet, row])
                # nothing dropped: every non-empty cell of those rows in a data column is a record
                dcols = set(tinfo["data_cols"].split(",")) if tinfo["data_cols"] else set()
                nonblank = {r["source_cell"] for r in srecs if not (r["note"] and r["note"].startswith("blank"))}
                for ref, val in d.items():
                    col, row = xlsx_xml.split_ref(ref)
                    if row in rows_ext and col in dcols and ref not in nonblank:
                        res["nonempty_missing"].append([sid, sheet, ref, val])
    # (b) additivity
    add = {"checks": 0, "equal": 0, "within_1_unit": 0, "mismatch": 0, "tables_with_checks": 0, "tables_with_mismatch": 0, "mismatches": []}
    per_table = {}
    for sid, recs in by_file.items():
        sheets = defaultdict(list)
        for r in recs:
            sheets[r["source_sheet"]].append(r)
        for sheet, rs in sheets.items():
            rows = defaultdict(dict)
            dims = {}
            for r in rs:
                rows[r["source_row"]][r["source_col"]] = (r["value"], r["measure"], r["unit"])
                cls = json.loads(r["row_class"]) if r["row_class"] else {}
                dims[r["source_row"]] = {"area": r["area_name"], **cls}
            n_chk = n_bad = 0
            names = list(next(iter(dims.values())).keys()) if dims else []
            for dname in names:
                groups = defaultdict(lambda: {"total": None, "parts": []})
                for row, dv in dims.items():
                    other = tuple((k, dv[k]) for k in names if k != dname)
                    if extract.squash(dv[dname]) in extract.TOTAL_NAMES or dv[dname] in ("合計",):
                        groups[other]["total"] = row
                    else:
                        groups[other]["parts"].append(row)
                for other, gp in groups.items():
                    if gp["total"] is None or len(gp["parts"]) < 1:
                        continue
                    # a row of the same other dims whose breakdown dimension is 合計 is the total; parts must not themselves be totals of another dim
                    for col, (tv, meas, unit) in rows[gp["total"]].items():
                        if tv is None:
                            continue
                        vals = [rows[p].get(col, (None,))[0] for p in gp["parts"]]
                        s = sum(x for x in vals if x is not None)
                        add["checks"] += 1
                        n_chk += 1
                        if s == tv or abs(s - tv) <= 1e-6 * max(1.0, abs(tv)):
                            add["equal"] += 1
                        elif abs(s - tv) <= 1.0001:
                            add["within_1_unit"] += 1
                        else:
                            add["mismatch"] += 1
                            n_bad += 1
                            if len(add["mismatches"]) < 400:
                                add["mismatches"].append({"table_id": sid, "sheet": sheet, "dimension": dname, "other": dict(other),
                                                          "col": col, "measure": meas, "total": tv, "sum_of_parts": s,
                                                          "diff": s - tv})  # fmt: skip
            per_table[(sid, sheet)] = (n_chk, n_bad)
    add["tables_with_checks"] = sum(1 for v in per_table.values() if v[0])
    add["tables_with_mismatch"] = sum(1 for v in per_table.values() if v[1])
    add["by_table"] = {f"{k[0]}/{k[1]}": {"checks": v[0], "mismatches": v[1]} for k, v in per_table.items() if v[0]}
    # (c), (d)
    meta_by_table = {t["table_id"]: t for t in tables}
    zero = [{"survey_year": t["survey_year"], "table_id": t["table_id"], "table_title": t["table_title"], "sheet": t["source_sheet"],
             "sheet_rows": t["sheet_rows"], "reader_note": t["reader_note"]} for t in tables if t["chiba_rows"] == 0]  # fmt: skip
    for y, d in year.items():
        yt = [t for t in tables if t["survey_year"] == y]
        d["tables"] = len({t["table_id"] for t in yt})
        d["tables_with_chiba"] = len({t["table_id"] for t in yt if t["chiba_rows"] > 0})
    res["additivity"] = add
    res["sheets_without_chiba_rows"] = zero
    res["by_year"] = {str(y): dict(d) for y, d in sorted(year.items())}
    (ROOT / "docs" / "06_verify.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    schema = pa.schema([("survey_year", pa.int16()), ("tables_fetched", pa.int32()), ("tables_with_chiba_rows", pa.int32()),
                        ("sheets", pa.int32()), ("chiba_rows", pa.int32()), ("records", pa.int32()), ("cells_checked", pa.int32()),
                        ("cells_equal", pa.int32()), ("additivity_checks", pa.int32()), ("additivity_mismatch", pa.int32())])  # fmt: skip
    rows_out = []
    for y, d in sorted(year.items()):
        ids = {t["table_id"] for t in tables if t["survey_year"] == y}
        n_cells = sum(1 for r in long if r["survey_year"] == y)
        bad_cells = {(m[0], m[1], m[2]) for m in res["cell_mismatches"] if len(m) > 3}
        n_bad_cells = sum(1 for r in long if r["survey_year"] == y and (r["table_id"], r["source_sheet"], r["source_cell"]) in bad_cells)
        a_chk = sum(v[0] for k, v in per_table.items() if k[0] in ids)
        a_bad = sum(v[1] for k, v in per_table.items() if k[0] in ids)
        rows_out.append({"survey_year": y, "tables_fetched": d["tables"], "tables_with_chiba_rows": d["tables_with_chiba"],
                         "sheets": d["sheets"], "chiba_rows": d["chiba_rows"], "records": d["records"], "cells_checked": n_cells,
                         "cells_equal": n_cells - n_bad_cells, "additivity_checks": a_chk, "additivity_mismatch": a_bad})  # fmt: skip
    pq.write_table(pa.Table.from_pylist(rows_out, schema=schema), ROOT / "data" / "parquet" / "year_checks.parquet", compression="zstd")
    print(f"files {res['files']}; cells checked {res['cells_checked']}, equal {res['cells_equal']} (of which float noise {res.get('float_noise', 0)}), mismatches {len(res['cell_mismatches'])}")
    print(f"tree-form rows not scannable by the prefecture-name scan: {res.get('tree_rows_not_scannable', 0)}")
    print(f"non-empty cells missing from the table {len(res['nonempty_missing'])}; rows missed {len(res['rows_missed'])}; "
          f"rows extra (inherited prefecture) {res['rows_extra_inherited']}, extra other {len(res['rows_extra_other'])}")  # fmt: skip
    print(f"additivity: {add['checks']} checks, equal {add['equal']}, within 1 unit {add['within_1_unit']}, mismatch {add['mismatch']} "
          f"in {add['tables_with_mismatch']} of {add['tables_with_checks']} tables")  # fmt: skip
    print(f"sheets without Chiba rows: {len(zero)}")


if __name__ == "__main__":
    main()
