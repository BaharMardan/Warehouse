"""Excel -> commodity-catalog rows, using ONLY the Python standard library.

The deploy image has no openpyxl/pandas (and this environment has no network to add
them), so an .xlsx is read as what it actually is: a zip of XML parts. We pull the
shared-string table and every worksheet, and yield one dict per commodity row.

The yearly HS workbook (کتاب+1403) splits its rows across 7 sheets ("Table 1".."Table 7")
that all share one layout. Only the first sheet carries a header row; the rest start at
data. Cells are read BY COLUMN LETTER (from each cell's r="B7" ref), never by position,
because empty cells are omitted from the XML and would otherwise shift a positional read.

Column layout (verified against the real file):
    A حقوق ورودی (import duty)      -- derived = customs+profit, NOT stored
    B واحد اندازه گیری (unit)
    C سود بازرگانی (commercial profit)
    D حقوق گمرکی (customs duty)
    E شرح فارسی (description)
    F ردیف تعرفه (HS code)
"""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# --- Persian normalization (shared by import AND search so both sides fold identically) ---
_DIGIT_MAP = {ord(c): str(i % 10) for i, c in enumerate(
    "۰۱۲۳۴۵۶۷۸۹" "٠١٢٣٤٥٦٧٨٩")}
_LETTER_MAP = {
    ord("ي"): "ی", ord("ك"): "ک",          # Arabic ye/kaf -> Persian
    ord("ـ"): None,                     # tatweel (ـ) -> drop
    ord("ة"): "ه", ord("ۀ"): "ه",
}
_STRIP_RE = re.compile(r"[‌‏‎]")   # ZWNJ / RTL/LTR marks
_DASH_RE = re.compile(r"[-‐-―]+")        # hyphen / en/em dashes -> space
_WS_RE = re.compile(r"\s+")


def normalize(text: str | None) -> str:
    """Fold a Persian string for search: unify ye/kaf, Latinize digits, strip tatweel,
    ZWNJ, indent dashes and redundant spaces, lowercase. Empty/None -> ''."""
    if not text:
        return ""
    s = text.translate(_DIGIT_MAP).translate(_LETTER_MAP)
    s = _STRIP_RE.sub("", s)
    s = _DASH_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip().lower()
    return s


def _col_letter(ref: str) -> str:
    """'B7' -> 'B'."""
    m = re.match(r"[A-Z]+", ref or "")
    return m.group(0) if m else ""


def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    name = "xl/sharedStrings.xml"
    if name not in z.namelist():
        return []
    root = ET.fromstring(z.read(name))
    out = []
    for si in root.findall(_NS + "si"):
        out.append("".join(t.text or "" for t in si.iter(_NS + "t")))
    return out


def _cell_text(c: ET.Element, shared: list[str]) -> str:
    t = c.get("t")
    v = c.find(_NS + "v")
    if v is None:
        inline = c.find(_NS + "is")
        if inline is not None:
            return "".join(x.text or "" for x in inline.iter(_NS + "t"))
        return ""
    if t == "s":
        idx = int(v.text)
        return shared[idx] if 0 <= idx < len(shared) else ""
    return v.text or ""


_HS_RE = re.compile(r"^\d{6,}$")   # a real tariff row is all digits, >=6 long


def parse_catalog(path: str) -> list[dict]:
    """Return commodity dicts: hs_code, description_fa, unit, customs_duty,
    commercial_profit. Rows whose HS-code cell isn't a digit run (header rows, blanks,
    stray notes) are skipped, so header detection needs no per-sheet special-casing."""
    z = zipfile.ZipFile(path)
    shared = _load_shared_strings(z)
    sheets = sorted(n for n in z.namelist()
                    if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    rows: list[dict] = []
    for sheet in sheets:
        root = ET.fromstring(z.read(sheet))
        data = root.find(_NS + "sheetData")
        if data is None:
            continue
        for r in data.findall(_NS + "row"):
            bycol: dict[str, str] = {}
            for c in r.findall(_NS + "c"):
                bycol[_col_letter(c.get("r", ""))] = _cell_text(c, shared)
            hs = (bycol.get("F") or "").strip()
            if not _HS_RE.match(hs):
                continue
            desc = (bycol.get("E") or "").strip()
            rows.append({
                "hs_code": hs,
                "description_fa": desc,
                "description_norm": normalize(desc),
                "unit": (bycol.get("B") or "").strip() or None,
                "commercial_profit": _num(bycol.get("C")),
                "customs_duty": _num(bycol.get("D")),
            })
    return rows


def _num(v):
    if v is None:
        return None
    s = str(v).translate(_DIGIT_MAP).strip()
    if s == "":
        return None
    try:
        return float(s) if ("." in s) else int(s)
    except ValueError:
        return None
