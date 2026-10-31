"""Read the Chiba rows of an e-Stat 水害統計調査 Excel sheet into long records (one cell of the table = one record).

The reader of this module is openpyxl (.xlsx) or xlrd (.xls). The check of scripts/06_verify.py reads the same cells again with
other code (zipfile + XML for .xlsx, pandas for .xls), so a bug here cannot confirm itself.

What is kept as in the table: the numbers (no unit conversion, a blank stays null, a symbol such as '-' gives value null and the symbol
in `symbol`), the names of regions (only whitespace is removed: the tables pad names with spaces, '千　葉'), and the header texts.
Header texts are collected per column from the top of the header down to the last header row, through merged cells and through
'center across selection' cells; wrapped text of one header cell that is cut over several rows stays as separate segments
(e.g. 公共土 / 木施設), joined by ' / '. `header_cells` lists the cells they come from.
"""

from __future__ import annotations

import json
import re
import unicodedata
import warnings
from dataclasses import dataclass, field
from pathlib import Path

PREF_STEMS = {
    "北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "新潟", "富山",
    "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根",
    "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄",
}  # fmt: skip
SYMBOLS = {"-", "－", "―", "ー", "…", "‥", "・", "x", "X", "ｘ", "Ｘ", "△", "▲", "*", "**", "***", "＊", "＊＊＊", "―", "‐", "−"}
TOTAL_NAMES = {"合計", "計", "全体", "総計"}
CODE_AREA_RE = re.compile(r"市区町村コード|市町村コード|団体コード|地域コード|自治体コード|地方公共団体コード")


def squash(s) -> str:
    """Remove every whitespace character (the tables pad and wrap with spaces, ideographic spaces and newlines)."""
    return re.sub(r"[\s　]+", "", str(s)).replace("_x001A_", "")


def pref_stem(s) -> str | None:
    t = squash(s)
    if not t:
        return None
    u = re.sub(r"[県府都]$", "", t) if t != "北海道" else t
    return u if u in PREF_STEMS else None


def col_letter(c: int) -> str:
    s = ""
    while c:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def coord(r: int, c: int) -> str:
    return f"{col_letter(c)}{r}"


@dataclass
class Grid:
    path: str
    sheet: str
    nrows: int
    ncols: int
    cells: dict = field(default_factory=dict)  # (row, col) 1-based -> value (str or float); empty cells are absent
    merges: list = field(default_factory=list)  # (r1, c1, r2, c2) 1-based inclusive
    center_across: set = field(default_factory=set)  # cells with the 'center across selection' alignment

    def get(self, r: int, c: int):
        return self.cells.get((r, c))


def _norm_value(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        return v if v.strip() != "" else None
    return str(v)


def open_grids(path: Path) -> list[Grid]:
    path = Path(path)
    if path.suffix == ".xlsx":
        import openpyxl

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wb = openpyxl.load_workbook(path, data_only=True)
        out = []
        for ws in wb.worksheets:
            g = Grid(path.name, ws.title, ws.max_row, ws.max_column)
            for row in ws.iter_rows():
                for cell in row:
                    v = _norm_value(cell.value)
                    if v is not None:
                        g.cells[(cell.row, cell.column)] = v
                    if cell.alignment is not None and cell.alignment.horizontal == "centerContinuous":
                        g.center_across.add((cell.row, cell.column))
            g.merges = [(m.min_row, m.min_col, m.max_row, m.max_col) for m in ws.merged_cells.ranges]
            out.append(g)
        return out
    if path.suffix == ".xls":
        import xlrd

        book = xlrd.open_workbook(str(path), formatting_info=True)
        out = []
        for sh in book.sheets():
            g = Grid(path.name, sh.name, sh.nrows, sh.ncols)
            for r in range(sh.nrows):
                for c in range(sh.ncols):
                    ctype = sh.cell_type(r, c)
                    if ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                        v = None
                    elif ctype == xlrd.XL_CELL_TEXT:
                        v = _norm_value(sh.cell_value(r, c))
                    elif ctype == xlrd.XL_CELL_NUMBER:
                        v = float(sh.cell_value(r, c))
                    else:  # date, bool, error: keep the text of the value so that nothing is silently dropped
                        v = f"<xlrd type {ctype}: {sh.cell_value(r, c)!r}>"
                    if v is not None:
                        g.cells[(r + 1, c + 1)] = v
                    xf = book.xf_list[sh.cell_xf_index(r, c)]
                    if xf.alignment.hor_align == 6:
                        g.center_across.add((r + 1, c + 1))
            g.merges = [(rlo + 1, clo + 1, rhi, chi) for rlo, rhi, clo, chi in sh.merged_cells]
            out.append(g)
        return out
    raise ValueError(f"unsupported file {path}")


def is_symbol(s: str) -> bool:
    return squash(s) in SYMBOLS


def find_pref_col(g: Grid) -> int | None:
    """The leftmost of the first 4 columns that holds at least 3 different prefecture names."""
    for c in range(1, min(g.ncols, 4) + 1):
        names = {pref_stem(g.get(r, c)) for r in range(1, g.nrows + 1) if isinstance(g.get(r, c), str)}
        names.discard(None)
        if len(names) >= 3:
            return c
    return None


def first_numeric_row(g: Grid) -> int | None:
    """The first row with at least 2 numbers."""
    for r in range(1, g.nrows + 1):
        if sum(1 for c in range(1, g.ncols + 1) if isinstance(g.get(r, c), float)) >= 2:
            return r
    return None


def first_name_row(g: Grid, pref_col: int) -> int | None:
    for r in range(1, g.nrows + 1):
        v = g.get(r, pref_col)
        if isinstance(v, str) and pref_stem(v):
            return r
    return None


def header_text(g: Grid, r: int, c: int) -> tuple[str, str] | None:
    """The header text that applies to cell (r, c): its own, that of the merged range it lies in, or that of the cell to the
    left whose centre-across span covers it. Returns (text, source cell) or None."""
    v = g.get(r, c)
    if isinstance(v, str):
        return squash(v), coord(r, c)
    if v is not None:
        return str(v), coord(r, c)
    for r1, c1, r2, c2 in g.merges:
        if r1 <= r <= r2 and c1 <= c <= c2:
            tl = g.get(r1, c1)
            return (squash(tl), coord(r1, c1)) if tl is not None else None
    if (r, c) in g.center_across:
        cc = c - 1
        while cc >= 1 and g.get(r, cc) is None and (r, cc) in g.center_across:
            cc -= 1
        if cc >= 1 and g.get(r, cc) is not None and (r, cc) in g.center_across:
            return squash(g.get(r, cc)), coord(r, cc)
    return None


UNIT_RE = re.compile(r"[（(]([^（）()]*?(?:円|㎡|m2|ha|棟|人|世帯|戸|件|cm|ｈａ|数|％|%|㎞|km|ｍ|m|ａ)[^（）()]*?)[）)]")
DITTO = "〃"
TREE_HEADER = ["都道府県名", "異常気象名", "（水害発生年月）", "水系・沿岸名"]
DATE_LIKE = re.compile(r"^[\d.．～~〜\-－ー]+$")


@dataclass
class Layout:
    sheet: str
    ncols: int
    sheet_title: str | None
    unit_note: str | None
    pref_col: int | None
    data_start: int | None
    header_rows: list
    key_cols: list
    data_cols: list
    ignored_label_cols: list
    footnotes: list
    hdr: dict
    hdr_sig: tuple
    tree: bool  # the legacy form: the first label column holds prefecture, event, date and river system names in turn
    note: str | None = None


def header_signature(g: Grid, rows: list) -> tuple:
    return tuple((r, c, squash(g.get(r, c))) for r in rows for c in range(1, g.ncols + 1) if isinstance(g.get(r, c), str))


def analyse(g: Grid, prev: Layout | None = None) -> Layout:
    pref_col = find_pref_col(g)
    nrow = first_numeric_row(g)
    if pref_col is None:
        # a continuation sheet (the rows of the sheet before go on) has no prefecture name at all: same header, same columns
        if prev is not None and prev.pref_col is not None and nrow is not None and g.ncols == prev.ncols:
            sig = header_signature(g, list(range(1, nrow)))
            if sig == prev.hdr_sig:
                lay = Layout(**{**prev.__dict__, "sheet": g.sheet, "data_start": nrow, "note": "continuation of the sheet before"})
                return lay
        return Layout(g.sheet, g.ncols, None, None, None, nrow, [], [], [], [], [], {}, (), False,
                      "no prefecture name in the sheet and no matching sheet before it")  # fmt: skip
    nm = first_name_row(g, pref_col)
    start = min(x for x in (nm, nrow) if x is not None)
    hdr_rows = list(range(1, start))
    # sheet title and unit note
    title, unit_note = None, None
    for r in hdr_rows:
        for c in range(1, g.ncols + 1):
            v = g.get(r, c)
            if isinstance(v, str) and "単位" in v:
                unit_note = squash(v)
    non_empty_rows = [r for r in hdr_rows if any(g.get(r, c) is not None for c in range(1, g.ncols + 1))]
    title_row = None
    if non_empty_rows:
        r0 = non_empty_rows[0]
        cells = [(c, g.get(r0, c)) for c in range(1, g.ncols + 1) if g.get(r0, c) is not None]
        txts = [squash(v) for _, v in cells if isinstance(v, str)]
        if (len(cells) <= 2 and len(non_empty_rows) > 1 and not any("単位" in t for t in txts) and all(isinstance(v, str) for _, v in cells)
                and (txts[0].startswith("表") or len(txts[0]) > 8)):  # fmt: skip
            title_row = r0
            title = "".join(txts)
    rows = range(start, g.nrows + 1)
    num, txt = {}, {}
    for r in rows:
        for c in range(1, g.ncols + 1):
            v = g.get(r, c)
            if v is None:
                continue
            if isinstance(v, float):
                num[c] = num.get(c, 0) + 1
            else:
                txt[c] = txt.get(c, 0) + 1
    hdr = {}
    for c in range(1, g.ncols + 1):
        segs = []
        for r in hdr_rows:
            if r == title_row:
                continue
            t = header_text(g, r, c)
            if t is None or not t[0] or "単位" in t[0]:
                continue
            if segs and segs[-1][0] == t[0]:
                segs[-1] = (t[0], segs[-1][1] + [t[1]])
                continue
            segs.append((t[0], [t[1]]))
        hdr[c] = segs
    key_cols, data_cols, ignored = [], [], []
    scanning_keys = True
    for c in range(1, g.ncols + 1):
        n, t = num.get(c, 0), txt.get(c, 0)
        htxt = "/".join(s for s, _ in hdr[c])
        if n == 0 and t == 0:
            continue
        if scanning_keys and (t > n or "コード" in htxt):
            key_cols.append(c)
            continue
        scanning_keys = False
        if n == 0 and t > 0 and not all(is_symbol(g.get(r, c)) for r in rows if isinstance(g.get(r, c), str)):
            ignored.append(c)  # a label column to the right of the data (a repeat of the row labels)
            continue
        data_cols.append(c)
    # the legacy tree form: the first label column holds, stacked in its header, 都道府県名 / 異常気象名 / （水害発生年月） / 水系・沿岸名
    tree = bool(key_cols) and [x for x, _ in hdr[key_cols[0]]][:4] == TREE_HEADER
    foot = []
    for r in range(start, g.nrows + 1):
        v = g.get(r, pref_col)
        if isinstance(v, str) and re.match(r"^\s*[注※＊*(（]?\s*(注|※)", v):
            foot.append(squash(v))
    return Layout(g.sheet, g.ncols, title, unit_note, pref_col, start, hdr_rows, key_cols, data_cols, ignored, foot, hdr,
                  header_signature(g, hdr_rows), tree)  # fmt: skip


def measure_of(hdr: dict, c: int) -> tuple[str, str, str | None]:
    segs = hdr.get(c, [])
    measure = " / ".join(s for s, _ in segs)
    cells = ",".join(dict.fromkeys(x for _, srcs in segs for x in srcs))
    unit = None
    for s, _ in reversed(segs):
        m = UNIT_RE.search(s)
        if m:
            unit = m.group(1)
            break
    return measure, cells, unit


def unit_of_note(note: str | None) -> str | None:
    """'（被害額単位：百万円）' -> '百万円'; None when the note has no 単位：."""
    if not note:
        return None
    m = re.search(r"単位[:：]\s*([^）)]+)", note)
    return m.group(1) if m else None


@dataclass
class State:
    """What goes on from one sheet of a workbook to the next: the layout, the prefecture of the rows above, the last label of each
    column (for the ditto mark 〃) and, in the legacy tree form, the event, the date and the river system."""

    layout: Layout | None = None
    pref: str | None = None
    last: dict = field(default_factory=dict)
    event: str | None = None
    date: str | None = None
    system: str | None = None


def _cls_value(v):
    if v is None:
        return None
    if isinstance(v, str):
        return squash(v)
    return int(v) if v == int(v) else v


def extract_grid(g: Grid, meta: dict, state: State | None = None) -> tuple[list[dict], dict]:
    """The long records of the Chiba rows of one sheet, and a dict that describes the sheet.

    Pass the same `state` for the sheets of one workbook, in order: a sheet that goes on with the rows of the sheet before it
    (same header, no prefecture name at its top) belongs to the prefecture of the last row above."""
    state = state if state is not None else State()
    lay = analyse(g, state.layout)
    desc = {"sheet": g.sheet, "sheet_title": lay.sheet_title, "unit_note": lay.unit_note, "note": lay.note,
            "key_cols": [col_letter(c) for c in lay.key_cols], "data_cols": [col_letter(c) for c in lay.data_cols],
            "ignored_label_cols": [col_letter(c) for c in lay.ignored_label_cols], "first_data_row": lay.data_start,
            "footnotes": lay.footnotes, "nrows": g.nrows, "ncols": g.ncols, "tree_form": lay.tree,
            "chiba_rows": 0, "inherited_rows": 0, "ditto_rows": 0, "orphan_rows": 0}  # fmt: skip
    if lay.pref_col is None or not lay.data_cols:
        return [], desc
    same_table = state.layout is not None and state.layout.hdr_sig == lay.hdr_sig and state.layout.ncols == lay.ncols
    if not same_table:  # a new table: nothing goes on from the sheet before
        state.pref, state.last, state.event, state.date, state.system = None, {}, None, None, None
    state.layout = lay
    key_names = {c: "/".join(s for s, _ in lay.hdr[c]) or f"col{col_letter(c)}" for c in lay.key_cols}
    tree_names = None
    if lay.tree:
        tree_names = TREE_HEADER  # prefecture, event, date, river system
    muni_col = next((c for c in lay.key_cols if re.search(r"市区町村|市町村", key_names[c]) and c != lay.pref_col), None)
    code_col = next((c for c in lay.key_cols if CODE_AREA_RE.search(key_names[c])), None)
    out, chiba_rows, inherited, dittos = [], set(), 0, 0
    for r in range(lay.data_start, g.nrows + 1):
        if not any(g.get(r, c) is not None for c in range(1, g.ncols + 1)):
            continue
        has_num = any(isinstance(g.get(r, c), float) for c in lay.data_cols)
        was_inherited, ditto_dims = False, []
        cls: dict = {}
        if lay.tree:
            c1 = lay.key_cols[0]
            v1 = g.get(r, c1)
            others = [c for c in lay.key_cols[1:] if g.get(r, c) is not None]
            t1 = squash(v1) if isinstance(v1, str) else None
            kind = "data"
            if t1 and not others:
                if t1 != DITTO and pref_stem(t1):
                    kind = "pref"
                elif DATE_LIKE.match(t1) and not has_num:
                    kind = "date"
                elif t1 != DITTO:
                    kind = "event"
            if kind == "pref":
                state.pref, state.event, state.date, state.system, state.last = t1, None, None, None, {}
            elif kind == "date":
                state.date = t1
                continue
            elif kind == "event":
                state.event, state.date, state.system, state.last = t1, None, None, {}
            else:
                if t1 and t1 != DITTO:
                    state.system = t1
                    state.last = {}
                elif t1 == DITTO:
                    ditto_dims.append(tree_names[3])
                for c in lay.key_cols[1:]:
                    v = g.get(r, c)
                    if isinstance(v, str) and squash(v) == DITTO:
                        v = state.last.get(c)
                        ditto_dims.append(key_names[c])
                    state.last[c] = v
            if state.pref is None and has_num:
                desc["orphan_rows"] += 1  # numbers before any prefecture name: the order of the sheets would be wrong
            if state.pref is None or pref_stem(state.pref) != "千葉" or not has_num and kind == "data":
                continue
            pref_label = squash(state.pref)
            cls[tree_names[1]] = state.event if kind != "pref" else None
            cls[tree_names[2]] = state.date if kind not in ("pref", "event") else None
            cls[tree_names[3]] = state.system if kind == "data" else None
            vals = {c: (state.last.get(c) if kind == "data" else None) for c in lay.key_cols[1:]}
            for c in lay.key_cols[1:]:
                if c != muni_col and c != code_col:
                    cls[key_names[c]] = _cls_value(vals[c])
            area_name = squash(vals[muni_col]) if muni_col and vals.get(muni_col) is not None else pref_label
            area_code = None
        else:
            pv = g.get(r, lay.pref_col)
            if pv is not None:
                state.pref = squash(pv)
            else:
                was_inherited = True
            if state.pref is None and has_num:
                desc["orphan_rows"] += 1
            if state.pref is None or pref_stem(state.pref) != "千葉":
                continue
            pref_label = state.pref
            vals = {}
            for c in lay.key_cols:
                v = g.get(r, c)
                if isinstance(v, str) and squash(v) == DITTO and c != lay.pref_col:
                    v = state.last.get(c)
                    ditto_dims.append(key_names[c])
                elif v is not None:
                    state.last[c] = v
                vals[c] = v
            area_name = squash(vals[muni_col]) if muni_col and vals.get(muni_col) is not None else pref_label
            area_code = None
            if code_col and vals.get(code_col) is not None:
                v = vals[code_col]
                area_code = str(int(v)) if isinstance(v, float) and v == int(v) else squash(v)
            for c in lay.key_cols:
                if c in (lay.pref_col, muni_col, code_col):
                    continue
                cls[key_names[c]] = _cls_value(vals[c])
        if was_inherited:
            inherited += 1
        if ditto_dims:
            dittos += 1
        chiba_rows.add(r)
        level = "municipality" if muni_col and area_name and area_name not in TOTAL_NAMES and area_name != pref_label else "prefecture"
        for c in lay.data_cols:
            v = g.get(r, c)
            measure, hcells, unit = measure_of(lay.hdr, c)
            rec = {**meta, "sheet": g.sheet, "sheet_title": lay.sheet_title, "pref_label": pref_label, "area_code": area_code,
                   "area_name": area_name, "level": level,
                   "row_class": json.dumps(cls, ensure_ascii=False) if cls else None, "measure": measure,
                   "col": col_letter(c), "header_cells": hcells, "value": None, "unit": unit or unit_of_note(lay.unit_note),
                   "symbol": None, "note": None, "source_row": r, "source_cell": coord(r, c)}  # fmt: skip
            notes = []
            if isinstance(v, float):
                rec["value"] = v
            elif isinstance(v, str):
                rec["symbol"] = v  # the text as in the cell
                if not is_symbol(v):
                    notes.append("text in a numeric column")
            else:
                notes.append("blank")
            if was_inherited:
                notes.append("prefecture name inherited from the row above")
            if ditto_dims:
                notes.append("ditto mark (〃) resolved from the row above in: " + ",".join(ditto_dims))
            if lay.tree:
                notes.append("rows in the hierarchical form: event, date and river system are those of the rows above")
            if lay.note:
                notes.append(lay.note)
            rec["note"] = "; ".join(notes) if notes else None
            out.append(rec)
    desc.update(chiba_rows=len(chiba_rows), inherited_rows=inherited, ditto_rows=dittos)
    return out, desc


SHEET_NO_RE = re.compile(r"^(公共土木|一般|公益)(\d+)$")


def in_reading_order(grids: list[Grid]) -> list[Grid]:
    """The sheets of a workbook in the order in which their rows go on. The tab order is that, except in a few workbooks whose
    tabs 公共土木N are not in the order of N (平成11, 12 and 13 公共土木施設水害統計基本表): those are read by N."""
    numbered = [g for g in grids if SHEET_NO_RE.match(g.sheet)]
    if len(numbered) < 2:
        return grids
    by_no = sorted(numbered, key=lambda g: (SHEET_NO_RE.match(g.sheet).group(1), int(SHEET_NO_RE.match(g.sheet).group(2))))
    it = iter(by_no)
    return [next(it) if SHEET_NO_RE.match(g.sheet) else g for g in grids]


def survey_year_of(label: str) -> int:
    t = unicodedata.normalize("NFKC", label)
    m = re.match(r"(令和|平成)(元|\d+)年", t)
    if not m:
        raise ValueError(label)
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return (2018 if m.group(1) == "令和" else 1988) + n


def table_no_of(title: str) -> str | None:
    t = unicodedata.normalize("NFKC", title).replace("ー", "-").replace("－", "-").replace("‐", "-")
    m = re.search(r"[（(]\s*(表[-\s]*[\d\-]+)\s*[）)]", t)
    return re.sub(r"\s+", "", m.group(1)) if m else None


def family_of(title: str) -> str:
    t = unicodedata.normalize("NFKC", title)
    return re.sub(r"[（(]\s*表[^）)]*[）)]", "", t).strip()
