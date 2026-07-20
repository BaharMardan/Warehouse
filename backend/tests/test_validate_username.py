import json
import os
from pathlib import Path

import oracledb
import pytest

from dotenv import load_dotenv

load_dotenv()
# ---------------------------------------------------------------------------
# 1. Connection — uses the SAME env vars as your app (.env)
# ---------------------------------------------------------------------------
def get_db_connection():
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_DSN"],
    )


# ---------------------------------------------------------------------------
# 2. The bridge: call the LIVE PL/SQL function.
#    Pointed at the throwaway demo function you create in Oracle.
# ---------------------------------------------------------------------------
def plsql_validate_username(conn, p_user_name):
    with conn.cursor() as cur:
        return cur.callfunc("gm_demo_validate_username", str, [p_user_name])


# ---------------------------------------------------------------------------
# 3. Inputs we deliberately lock down — the edges where a rewrite drifts.
# ---------------------------------------------------------------------------
INPUT_CASES = [
    "admin",
    "ali",
    "a",
    "",
    "   ",
    "user with spaces",
    "علی",                        # Persian input
    "x" * 100,                    # very long
    "Robert'); DROP TABLE x;--",  # nasty input
    None,                         # NULL
]

GOLDEN_FILE = Path(__file__).parent / "golden" / "validate_username.json"


def run_cases(impl, conn=None):
    """Run every input through an implementation; capture value OR error."""
    out = {}
    for case in INPUT_CASES:
        try:
            value = impl(conn, case) if conn is not None else impl(case)
            out[repr(case)] = {"ok": value}
        except Exception as exc:
            out[repr(case)] = {"error": str(exc)[:120]}
    return out


def assert_matches_golden(results: dict):
    """First run records the snapshot; later runs compare against it."""
    if not GOLDEN_FILE.exists():
        GOLDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        # GOLDEN_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        GOLDEN_FILE.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        pytest.skip("Golden master created. Run pytest again to compare against it.")
    # expected = json.loads(GOLDEN_FILE.read_text())
    expected = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
    assert results == expected


# ---------------------------------------------------------------------------
# 4. TEST A — freezes the live PL/SQL behavior. Run this now.
# ---------------------------------------------------------------------------
def test_plsql_matches_golden():
    conn = get_db_connection()
    try:
        results = run_cases(plsql_validate_username, conn)
    finally:
        conn.close()
    assert_matches_golden(results)


# ---------------------------------------------------------------------------
# 5. TEST B — your future Python port (enable in Phase 6).
# ---------------------------------------------------------------------------
def python_validate_username(p_user_name):
    raise NotImplementedError  # you'll write this in Phase 6


@pytest.mark.skip(reason="Enable when you start the Python port (Phase 6).")
def test_python_matches_golden():
    results = run_cases(python_validate_username)
    assert_matches_golden(results)
