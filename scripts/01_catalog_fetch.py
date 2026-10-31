#!/usr/bin/env python3
"""Fetch the file-list pages of e-Stat for toukei=00600590 (水害統計調査): top, every survey year (tstat), every tclass1.

    uv run python scripts/01_catalog_fetch.py [YYYY-MM-DD]

Pages are saved verbatim under raw/<date>/listing/ with their headers in listing/_index.json. One request at a time, 2 s apart.
Resumable: an existing page is not fetched again.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import estat

ROOT = Path(__file__).parents[1]
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-31"
L = ROOT / "raw" / DATE / "listing"
IDX = L / "_index.json"


def get(name: str, url: str, index: dict) -> str:
    p = L / name
    if name in index and p.exists():
        return p.read_text(encoding="utf-8")
    status, headers, body = estat.fetch(url)
    if status != 200:
        raise SystemExit(f"HTTP {status} for {url}")
    p.write_bytes(body)
    index[name] = {"url": url, "fetched_at": estat.now(), "status": status, "bytes": len(body),
                   "sha256": estat.sha256_bytes(body), "last_modified": headers.get("Last-Modified")}
    IDX.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n")
    return body.decode("utf-8")


def main() -> None:
    L.mkdir(parents=True, exist_ok=True)
    index = json.loads(IDX.read_text()) if IDX.exists() else {}
    top = get("top.html", f"{estat.BASE}/stat-search/files?toukei=00600590", index)
    years = estat.parse_top(top)
    print(len(years), "survey years")
    for y in years:
        t = y["tstat"]
        yp = get(f"{t}.html", f"{estat.BASE}/stat-search/files?page=1&toukei=00600590&tstat={t}", index)
        links = estat.parse_tclass_links(yp)
        print(t, y["title"], y["n_files"], "files;", len(links), "tclass1:", [(k["tclass1"], k["n"]) for k in links], flush=True)
        for k in links:
            get(f"{t}__{k['tclass1']}.html", estat.BASE + k["href"], index)


if __name__ == "__main__":
    main()
