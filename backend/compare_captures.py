"""Compare two data captures and report any difference.

    python compare_captures.py sql/data sql/verify

Both directories are produced by extract_data.py -- one from the source
database, one re-captured from the restored copy. Because extract_data.py
orders rows by primary key and formats values deterministically, a correct
restore produces byte-identical files. That is a far stronger check than
comparing row counts: it catches truncated Persian text, mangled encodings,
date precision loss and numeric rounding, none of which change a count.

Exit status is 0 when the captures match and 1 when they do not.
"""

import argparse
import difflib
import hashlib
import os
import sys


def _sql_files(directory: str) -> dict[str, str]:
    """Per-table capture files, keyed by name. The manifest and the generated
    scripts are excluded: they carry timestamps and counter values that
    legitimately differ between two captures."""
    skip = {"load.sql", "99_resync_counters.sql", "README.md"}
    return {
        name: os.path.join(directory, name)
        for name in sorted(os.listdir(directory))
        if name.endswith(".sql") and name not in skip
    }


def _digest(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _rows(path: str) -> int:
    with open(path, encoding="utf-8") as handle:
        return sum(1 for line in handle if line.startswith("INSERT INTO"))


def _first_difference(left: str, right: str, name: str) -> list[str]:
    with open(left, encoding="utf-8") as handle:
        a = handle.readlines()
    with open(right, encoding="utf-8") as handle:
        b = handle.readlines()
    diff = difflib.unified_diff(a, b, fromfile=f"source/{name}", tofile=f"copy/{name}", n=1)
    return [line.rstrip("\n") for line in list(diff)[:14]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="capture from the original database")
    parser.add_argument("copy", help="capture from the restored database")
    parser.add_argument(
        "--quiet", action="store_true", help="report only tables that differ"
    )
    args = parser.parse_args()

    for directory in (args.source, args.copy):
        if not os.path.isdir(directory):
            parser.error(f"{directory} is not a directory")

    source = _sql_files(args.source)
    copy = _sql_files(args.copy)

    missing = sorted(set(source) - set(copy))
    extra = sorted(set(copy) - set(source))
    differing = []
    identical = 0
    total_rows = 0

    for name in sorted(set(source) & set(copy)):
        rows = _rows(source[name])
        total_rows += rows
        if _digest(source[name]) == _digest(copy[name]):
            identical += 1
            if not args.quiet:
                print(f"  ok    {name[:-4]} ({rows:,} rows)")
        else:
            differing.append(name)
            print(f"  DIFF  {name[:-4]} ({rows:,} rows source, {_rows(copy[name]):,} copy)")

    for name in missing:
        print(f"  MISSING in copy: {name[:-4]}")
    for name in extra:
        print(f"  EXTRA in copy:   {name[:-4]}")

    print()
    print(f"  identical: {identical}")
    print(f"  differing: {len(differing)}")
    if missing or extra:
        print(f"  missing:   {len(missing)}")
        print(f"  extra:     {len(extra)}")

    if differing:
        print("\nFirst difference in each table that differs:")
        for name in differing:
            print(f"\n--- {name} ---")
            for line in _first_difference(source[name], copy[name], name):
                print(f"  {line}")

    if differing or missing or extra:
        print("\nCAPTURES DIFFER")
        sys.exit(1)

    print(f"\nIDENTICAL -- {total_rows:,} rows match byte for byte")


if __name__ == "__main__":
    main()
