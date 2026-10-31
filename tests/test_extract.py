"""Tests of scripts/extract.py on small workbooks built here (no network, no raw files)."""

import openpyxl
import pytest
from openpyxl.styles import Alignment

import extract
import xlsx_xml

PREFS = ["北海道", "青森県", "岩手県", "宮城県", "千葉県", "東京都"]


def wb_path(tmp_path, build):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    build(wb)
    p = tmp_path / "t.xlsx"
    wb.save(p)
    return p


def test_squash_and_pref_stem():
    assert extract.squash("  千　葉 \n") == "千葉"
    assert extract.pref_stem("千葉県") == "千葉"
    assert extract.pref_stem("  千　葉  ") == "千葉"
    assert extract.pref_stem("京都府") == "京都"
    assert extract.pref_stem("北海道") == "北海道"
    assert extract.pref_stem("千葉市") is None
    assert extract.pref_stem("東北") is None


def test_survey_year_and_table_no():
    assert extract.survey_year_of("令和５年水害統計調査") == 2023
    assert extract.survey_year_of("令和元年水害統計調査") == 2019
    assert extract.survey_year_of("平成５年水害統計調査") == 1993
    assert extract.survey_year_of("平成２２年水害統計調査（「公共土木施設水害統計調査」は…）") == 2010
    assert extract.table_no_of("市区町村別水害被害（表ｰ３）") == "表-3"
    assert extract.table_no_of("主要異常気象別都道府県別水害被害（表-１１-２）") == "表-11-2"
    assert extract.table_no_of("一般資産等水害統計基本表") is None
    assert extract.family_of("市区町村別水害被害（表ｰ３）") == "市区町村別水害被害"


def prefecture_table(wb):
    ws = wb.create_sheet("hyo2")
    ws["A1"] = "表－２　都道府県別水害被害"
    ws["C2"] = "（被害額単位：百万円）"
    ws["B3"] = "死傷者数"
    ws.merge_cells("B3:C3")
    ws["D3"] = "一般資産等被害額"  # centre across selection: D3 spans D..E
    ws["D3"].alignment = Alignment(horizontal="centerContinuous")
    ws["E3"].alignment = Alignment(horizontal="centerContinuous")
    ws["A4"] = "都道"
    ws["A5"] = "府県名"
    for col, t in zip("BCDE", ["死者", "負傷者", "一般資産", "計"]):
        ws[f"{col}5"] = t
    for i, name in enumerate(PREFS):
        r = 6 + i
        ws[f"A{r}"] = name
        ws[f"B{r}"] = i
        ws[f"C{r}"] = None if name == "千葉県" else 1
        ws[f"D{r}"] = "-" if name == "千葉県" else 5.5
        ws[f"E{r}"] = 10 * i
    ws["F5"] = "府県名"  # a repeat of the labels at the right edge
    for i, name in enumerate(PREFS):
        ws[f"F{6 + i}"] = name


def test_prefecture_table(tmp_path):
    p = wb_path(tmp_path, prefecture_table)
    (g,) = extract.open_grids(p)
    recs, d = extract.extract_grid(g, {})
    assert d["chiba_rows"] == 1 and d["key_cols"] == ["A"] and d["data_cols"] == ["B", "C", "D", "E"]
    assert d["ignored_label_cols"] == ["F"]
    by = {r["source_cell"]: r for r in recs}
    assert set(by) == {"B10", "C10", "D10", "E10"}  # Chiba is the 5th prefecture: row 10
    assert by["B10"]["value"] == 4.0 and by["B10"]["measure"] == "死傷者数 / 死者"
    assert by["C10"]["value"] is None and by["C10"]["symbol"] is None and by["C10"]["note"] == "blank"
    assert by["D10"]["value"] is None and by["D10"]["symbol"] == "-"
    assert by["D10"]["measure"] == "一般資産等被害額 / 一般資産"  # through the centre-across span
    assert by["C10"]["measure"] == "死傷者数 / 負傷者"  # through the merged range
    assert by["E10"]["unit"] == "百万円" and by["E10"]["level"] == "prefecture" and by["E10"]["area_name"] == "千葉県"
    assert d["sheet_title"] == "表－２都道府県別水害被害"


def municipal_table(wb):
    ws = wb.create_sheet("hyo3")
    ws["A1"] = "表－３　市区町村別水害被害"
    ws["A3"], ws["B3"], ws["C3"] = "都道府県", "市区町村", "水害区域面積（㎡）"
    rows = [("北海道", "札幌市", 1), ("青森県", "青森市", 2), ("岩手県", "盛岡市", 3), ("千葉県", "千葉市中央区", 10),
            ("千葉県", "船橋市", 20), ("千葉県", "合計", 30), ("東京都", "合計", 99)]  # fmt: skip
    for i, (a, b, c) in enumerate(rows):
        ws[f"A{5 + i}"], ws[f"B{5 + i}"], ws[f"C{5 + i}"] = a, b, c


def test_municipal_table_levels(tmp_path):
    p = wb_path(tmp_path, municipal_table)
    (g,) = extract.open_grids(p)
    recs, d = extract.extract_grid(g, {})
    assert d["chiba_rows"] == 3 and len(recs) == 3
    assert [(r["area_name"], r["level"], r["value"]) for r in recs] == [("千葉市中央区", "municipality", 10.0), ("船橋市", "municipality", 20.0),
                                                                          ("合計", "prefecture", 30.0)]  # fmt: skip
    assert all(r["unit"] == "㎡" for r in recs)
    assert all(r["area_code"] is None for r in recs)  # the table has no area code: none is invented


def blank_pref_table(wb):
    ws = wb.create_sheet("t")
    ws["A3"], ws["B3"], ws["C3"] = "県名", "市区町村名", "被害額"
    data = [("北海道", "a", 1), (None, "b", 2), ("千葉県", "c", 3), (None, "d", 4), (None, "合計", 7), ("東京都", "e", 5), ("青森県", "f", 6),
            ("岩手県", "g", 7)]  # fmt: skip
    for i, (a, b, c) in enumerate(data):
        ws[f"A{5 + i}"], ws[f"B{5 + i}"], ws[f"C{5 + i}"] = a, b, c


def test_prefecture_name_on_the_first_row_only(tmp_path):
    p = wb_path(tmp_path, blank_pref_table)
    (g,) = extract.open_grids(p)
    recs, d = extract.extract_grid(g, {})
    assert d["chiba_rows"] == 3 and d["inherited_rows"] == 2
    assert [r["area_name"] for r in recs] == ["c", "d", "合計"]
    assert recs[1]["note"] == "prefecture name inherited from the row above"


def legacy_tree(wb):
    def sheet(name, rows):
        ws = wb.create_sheet(name)
        ws["B3"], ws["C3"], ws["D3"], ws["E3"], ws["F3"] = "都道府県名", "河川・海岸名等", "市区町村名", "被害額", "計"
        ws["B4"] = "異常気象名"
        ws["B5"] = "（水害発生年月）"
        ws["B6"] = "水系・沿岸名"
        for i, row in enumerate(rows):
            for col, v in zip("BCDE", row):
                if v is not None:
                    ws[f"{col}{7 + i}"] = v
            if row[3] is not None:
                ws[f"F{7 + i}"] = row[3] * 2

    sheet("公共土木1", [
        (" 北海道", None, None, 100), ("    台風", None, None, 100), ("    9.1", None, None, None),
        (" 石狩川", "石狩川", "札幌市", 100), (" 青森県", None, None, 50), (" 岩手県", None, None, 60)])  # fmt: skip
    sheet("公共土木2", [
        (" 千葉県", None, None, 1000), ("    豪雨", None, None, 1000), ("    10.5", None, None, None),
        (" 利根川", "合 計", None, 1000), ("    〃", "利根川", "合 計", 1000), ("    〃", "    〃", "市川市", 400)])  # fmt: skip
    sheet("公共土木3", [
        ("    〃", "    〃", "船橋市", 600), (" 東京都", None, None, 5), (" 神奈川県", None, None, 5)])  # fmt: skip


def test_legacy_tree_form_goes_on_in_the_next_sheet(tmp_path):
    p = wb_path(tmp_path, legacy_tree)
    state = extract.State()
    recs = []
    descs = []
    for g in extract.in_reading_order(extract.open_grids(p)):
        r, d = extract.extract_grid(g, {}, state)
        recs += r
        descs.append(d)
    assert all(d["orphan_rows"] == 0 for d in descs)
    assert descs[2]["chiba_rows"] == 1  # the first row of sheet 3 is Chiba's: the prefecture goes on from sheet 2
    import json

    got = [(r["sheet"], r["source_row"], r["area_name"], r["level"], json.loads(r["row_class"]), r["value"]) for r in recs]
    # prefecture row, event row, three data rows (the date row has no numbers), then sheet 3's first row
    rows = {(x[0], x[1]): x[2] for x in got}  # one record per data column: count rows
    assert list(rows.values()).count("船橋市") == 1 and list(rows.values()).count("市川市") == 1
    assert len(rows) == 6  # prefecture, event, 利根川 合計, 〃 利根川 合計, 市川市, 船橋市
    ichikawa = next(x for x in got if x[2] == "市川市")
    assert ichikawa[4]["異常気象名"] == "豪雨" and ichikawa[4]["水系・沿岸名"] == "利根川" and ichikawa[4]["河川・海岸名等"] == "利根川"
    assert ichikawa[5] == 400.0
    funabashi = next(x for x in got if x[2] == "船橋市")
    assert funabashi[0] == "公共土木3" and funabashi[4]["水系・沿岸名"] == "利根川" and funabashi[4]["異常気象名"] == "豪雨"


def test_tab_order_of_numbered_sheets(tmp_path):
    def build(wb):
        for n in ("公共土木3", "公共土木2", "公共土木1", "原本"):
            wb.create_sheet(n)

    p = wb_path(tmp_path, build)
    assert [g.sheet for g in extract.in_reading_order(extract.open_grids(p))] == ["公共土木1", "公共土木2", "公共土木3", "原本"]


def test_second_reader_agrees(tmp_path):
    p = wb_path(tmp_path, prefecture_table)
    cells = xlsx_xml.cells(p)["hyo2"]
    assert cells["A10"] == "千葉県" and cells["B10"] == 4.0 and cells["D10"] == "-" and "C10" not in cells
    (g,) = extract.open_grids(p)
    for (r, c), v in g.cells.items():
        assert cells[extract.coord(r, c)] == v


def test_no_prefecture_rows(tmp_path):
    def build(wb):
        ws = wb.create_sheet("total")
        ws["A2"], ws["B2"] = "全 国 計", 5
        ws["A3"], ws["B3"] = "x", 6

    (g,) = extract.open_grids(wb_path(tmp_path, build))
    recs, d = extract.extract_grid(g, {})
    assert recs == [] and "no prefecture name" in d["note"]


@pytest.mark.parametrize("text,unit", [("水害区域面積（㎡）", "㎡"), ("被災家屋棟数（棟）", "棟"), ("一般資産等被害額（千円）", "千円"), ("死者", None)])
def test_unit_in_header(text, unit):
    m = extract.UNIT_RE.search(text)
    assert (m.group(1) if m else None) == unit


def test_header_repeated_inside_the_data_is_not_a_row(tmp_path):
    def build(wb):
        ws = wb.create_sheet("t")
        ws["A3"], ws["B3"], ws["C3"] = "県名", "被害額", "計"
        rows = [("北海道", 1, 1), ("青森県", 1, 1), ("千葉県", 2, 2), ("県名", "被害額", "計"), (None, 3, 3), ("東京都", 4, 4)]
        for i, row in enumerate(rows):
            for col, v in zip("ABC", row):
                if v is not None:
                    ws[f"{col}{5 + i}"] = v

    (g,) = extract.open_grids(wb_path(tmp_path, build))
    recs, d = extract.extract_grid(g, {})
    assert d["chiba_rows"] == 2 and {r["source_row"] for r in recs} == {7, 9}  # the repeated header row 8 is skipped, row 9 goes on
    assert all(r["symbol"] is None for r in recs)
