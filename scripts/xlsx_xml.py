"""A second, independent reader of .xlsx cells: zipfile + ElementTree, no openpyxl, no pandas.

cells(path) -> {sheet name: {"B19": float | str}}   empty cells are absent
"""

import re
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}  # fmt: skip
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _text(si) -> str:
    return "".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))


def cells(path) -> dict:
    out = {}
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = [_text(si) for si in root.findall("m:si", NS)]
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = {r.get("Id"): r.get("Target") for r in rels}
        for sh in wb.find("m:sheets", NS):
            t = target[sh.get(RNS)]
            t = t.lstrip("/")
            part = t if t.startswith("xl/") else "xl/" + t
            d = {}
            for _, el in ET.iterparse(z.open(part)):
                if el.tag != "{%s}c" % NS["m"]:
                    continue
                ref, typ = el.get("r"), el.get("t")
                v = el.find("m:v", NS)
                if typ == "inlineStr":
                    is_ = el.find("m:is", NS)
                    val = _text(is_) if is_ is not None else None
                elif v is None or v.text is None:
                    val = None
                elif typ == "s":
                    val = shared[int(v.text)]
                elif typ in ("str", "e"):
                    val = v.text
                elif typ == "b":
                    val = float(v.text)
                else:
                    val = float(v.text)
                if isinstance(val, str) and val.strip() == "":
                    val = None
                if val is not None:
                    d[ref] = val
                el.clear()
            out[sh.get("name")] = d
    return out


def split_ref(ref: str) -> tuple[str, int]:
    m = re.fullmatch(r"([A-Z]+)(\d+)", ref)
    return m.group(1), int(m.group(2))
