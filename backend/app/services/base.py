from app.core.db import get_connection


def fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            columns = [col[0].lower() for col in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def fetch_one(sql: str, params: dict | None = None) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: dict | None = None) -> int:
    """Run an INSERT/UPDATE/DELETE. Returns how many rows changed."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            affected = cur.rowcount
        conn.commit()
        return affected


def insert_returning_id(sql: str, params: dict, out_key: str = "new_id") -> int:
    """Run an INSERT ... RETURNING <id> INTO :new_id, return the new id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            new_id = cur.var(int)
            cur.execute(sql, {**params, out_key: new_id})
        conn.commit()
        return new_id.getvalue()[0]