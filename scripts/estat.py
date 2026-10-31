"""Shared helpers: polite fetch of www.e-stat.go.jp (one request at a time, 2 s apart) and parsing of the file-list pages."""

import hashlib
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

BASE = "https://www.e-stat.go.jp"
UA = "Mozilla/5.0 (research; yuiseki)"
PAUSE = 2.0
_last = [0.0]


class Blocked(SystemExit):
    pass


def fetch(url: str) -> tuple[int, dict, bytes]:
    """GET with a 2 s gap since the previous request. A 403/429 stops the whole run (no workaround)."""
    wait = PAUSE - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            status, headers, body = r.status, dict(r.headers.items()), r.read()
    except urllib.error.HTTPError as e:
        _last[0] = time.time()
        if e.code in (401, 403, 429):
            raise Blocked(f"STOP: HTTP {e.code} for {url}") from e
        return e.code, dict(e.headers.items()), e.read()
    _last[0] = time.time()
    return status, headers, body


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def text_of(fragment: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_top(html: str) -> list[dict]:
    """The survey years (tstat) of the top page: tstat, title, number of files, publication date."""
    out = []
    for p in re.split(r'<a href="/stat-search/files\?toukei=00600590&amp;tstat=', html)[1:]:
        t = re.match(r"(\d+)", p).group(1)
        m = re.search(r'js-item_child"\s*data-key="tstat"\s*data-value="\d+">\s*(.*?)<span class="stat-pc">\[(\d+)件\]', p, re.S)
        d = re.search(r"(\d{4}-\d\d-\d\d)", p)
        out.append({"tstat": t, "title": text_of(m.group(1)), "n_files": int(m.group(2)), "date": d.group(1) if d else None})
    return out


def parse_tclass_links(html: str) -> list[dict]:
    """The tclass1 categories (cycle) on a survey-year page."""
    out, seen = [], set()
    for m in re.finditer(r'href="(/stat-search/files\?[^"]*tclass1=(\d+)[^"]*)"[^>]*>(.*?)</a>', html, re.S):
        if m.group(2) in seen:
            continue
        seen.add(m.group(2))
        txt = text_of(m.group(3))
        n = re.search(r"\[(\d+)件\]", txt)
        out.append({"tclass1": m.group(2), "href": unescape(m.group(1)), "label": txt, "n": int(n.group(1)) if n else None})
    return out


def parse_datalist(html: str) -> list[dict]:
    """A datalist page: the group headings and the files (statInfId, title, survey month, dates, formats)."""
    rows, group = [], None
    for art in re.findall(r'<article class="stat-dataset_list-item">(.*?)</article>', html, re.S):
        g = re.search(r'stat-dataset_list-group-item">(.*?)</li>', art, re.S)
        if g:
            group = text_of(g.group(1))
            continue
        a = re.search(r'stat_infid=(\d+)"[^>]*>(.*?)</a>', art, re.S)
        if not a:
            continue
        ym = re.search(r"調査年月.*?</span>\s*([^<]*)</div>", art, re.S)
        pub = re.search(r"公開（更新）日.*?</span>\s*(\d{4}-\d\d-\d\d)", art, re.S)
        # groups of the regex: 1 statInfId, 2 fileKind, 3 file_id, 4 release_count, 5 type
        fmts = [{"format": f.group(5), "file_kind": f.group(2), "file_id": f.group(3), "release_count": int(f.group(4))}
                for f in re.finditer(
                    r'<a href="/stat-search/file-download\?statInfId=(\d+)&(?:amp;)?fileKind=(\d+)"[^>]*?data-file_id="(\d+)"[^>]*?'
                    r'data-release_count="(\d+)"[^>]*?data-file_type="(\w+)"', art, re.S)]
        rows.append({"group": group, "statInfId": a.group(1), "title": text_of(a.group(2)),
                     "survey_ym": text_of(ym.group(1)) if ym else None, "published": pub.group(1) if pub else None,
                     "formats": fmts})
    return rows
