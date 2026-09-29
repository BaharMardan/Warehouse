"""Import only border names and Persian country names from the supplied workbooks.

Defaults to a read-only preview. Pass --apply to commit missing active terms.
Existing terms and references are preserved.
"""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def names_from_excel(path: Path, heading: str) -> list[str]:
    with ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(t.text or "" for t in item.findall(".//m:t", NS))
                       for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", NS)]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        column = None
        names = []
        for row in sheet.findall("m:sheetData/m:row", NS):
            cells = {}
            for cell in row.findall("m:c", NS):
                key = "".join(c for c in cell.attrib["r"] if c.isalpha())
                value = cell.find("m:v", NS)
                text = value.text if value is not None else ""
                if cell.get("t") == "s":
                    text = strings[int(text)]
                elif cell.get("t") == "inlineStr":
                    text = "".join(t.text or "" for t in cell.findall(".//m:t", NS))
                cells[key] = (text or "").strip()
            if column is None:
                column = next((key for key, value in cells.items() if value == heading), None)
            elif cells.get(column):
                names.append(cells[column])
        if column is None or not names:
            raise ValueError(f"Missing heading or names: {heading}")
        return list(dict.fromkeys(names))


def normalized(name):
    return " ".join(name.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ").split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--borders", required=True, type=Path)
    parser.add_argument("--countries", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    groups = {
        1: names_from_excel(args.borders, "نام مرز / گذرگاه"),
        2: names_from_excel(args.countries, "نام فارسی"),
    }
    from app.core.db import get_connection
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                if args.apply:
                    cur.execute("LOCK TABLE FA_SYS_TERMS IN EXCLUSIVE MODE")
                for category, names in groups.items():
                    cur.execute("""SELECT SYS_TERM_CATEGORY_ID FROM FA_SYS_TERM_CATEGORIES
                        WHERE SYS_TERM_CATEGORY_ID = :id AND SYS_TERM_CATEGORY_IS_DELETED = 'no'""",
                        {"id": category})
                    if not cur.fetchone():
                        raise ValueError(f"Active category {category} not found")
                    cur.execute("""SELECT SYS_TERM_VALUE, SYS_TERM_ORDER FROM FA_SYS_TERMS
                        WHERE SYS_TERM_CATEGORY_ID = :id AND SYS_TERM_IS_DELETED = 'no'""",
                        {"id": category})
                    existing = cur.fetchall()
                    known = {normalized(row[0] or "") for row in existing}
                    order = max((row[1] or 0 for row in existing), default=0)
                    missing = []
                    for name in names:
                        if normalized(name) not in known:
                            missing.append(name)
                            known.add(normalized(name))
                    print(f"Category {category}: source={len(names)}, existing={len(existing)}, missing={len(missing)}")
                    if args.apply:
                        for name in missing:
                            order += 1
                            cur.execute("""INSERT INTO FA_SYS_TERMS
                                (SYS_TERM_CATEGORY_ID, SYS_TERM_KEY, SYS_TERM_VALUE,
                                 SYS_TERM_STATUS, SYS_TERM_IS_DELETED, SYS_TERM_ORDER, SYS_TERM_CREATED_AT)
                                VALUES (:category, (SELECT TO_CHAR(NVL(MAX(SYS_TERM_ID), 0) + 1)
                                    FROM FA_SYS_TERMS), :name, 'active', 'no', :position, SYSDATE)""",
                                {"category": category, "name": name, "position": order})
                        cur.execute("""SELECT SYS_TERM_VALUE FROM FA_SYS_TERMS
                            WHERE SYS_TERM_CATEGORY_ID = :id AND SYS_TERM_IS_DELETED = 'no'""",
                            {"id": category})
                        saved = {normalized(row[0] or "") for row in cur.fetchall()}
                        if not all(normalized(name) in saved for name in names):
                            raise RuntimeError(f"Verification failed for category {category}")
            if args.apply:
                conn.commit()
                print("Committed and verified both lists.")
        except Exception:
            conn.rollback()
            raise


if __name__ == "__main__":
    main()
