# from dataclasses import dataclass


# @dataclass
# class Audit:
#     """Exact DB names of the audit / soft-delete columns. Oracle stores unquoted
#     names UPPERCASE, so the defaults are uppercase. Set any field to None to disable
#     that piece; pass audit=None to make_crud_router for a table with no audit columns."""
#     is_deleted: str | None = "IS_DELETED"
#     create_at: str | None = "CREATE_AT"
#     create_by: str | None = "CREATE_BY"
#     modify_at: str | None = "MODIFY_AT"
#     modify_by: str | None = "MODIFY_BY"


# _OFF = Audit(None, None, None, None, None)


# def _q(name: str) -> str:
#     return f'"{name}"'


# def plan(*, table, pk, fields, overrides=None, audit=Audit()):
#     overrides = overrides or {}
#     a = audit or _OFF

#     def column(f):                      # exact DB column for a field
#         return overrides.get(f, f.upper())

#     qtable, qpk = _q(table), _q(pk)

#     sel = [qpk]
#     for f in fields:
#         c = column(f)
#         sel.append(_q(c) if f == c.lower() else f"{_q(c)} AS {f}")
#     for c in (a.create_at, a.create_by, a.modify_at, a.modify_by):
#         if c:
#             sel.append(_q(c))
#     select_list = ", ".join(sel)

#     where_active = f" WHERE {_q(a.is_deleted)} = 'no'" if a.is_deleted else ""
#     and_active = f" AND {_q(a.is_deleted)} = 'no'" if a.is_deleted else ""

#     icols = [qpk] + [_q(column(f)) for f in fields]
#     ivals = [f"(SELECT NVL(MAX({qpk}), 0) + 1 FROM {qtable})"] + [f":{f}" for f in fields]
#     if a.is_deleted:
#         icols.append(_q(a.is_deleted)); ivals.append("'no'")
#     if a.create_at:
#         icols.append(_q(a.create_at)); ivals.append("SYSDATE")
#     if a.create_by:
#         icols.append(_q(a.create_by)); ivals.append(":actor_id")

#     sets = [f"{_q(column(f))} = :{f}" for f in fields]
#     if a.modify_at:
#         sets.append(f"{_q(a.modify_at)} = SYSDATE")
#     if a.modify_by:
#         sets.append(f"{_q(a.modify_by)} = :actor_id")

#     if a.is_deleted:
#         dsets = [f"{_q(a.is_deleted)} = 'yes'"]
#         if a.modify_at:
#             dsets.append(f"{_q(a.modify_at)} = SYSDATE")
#         if a.modify_by:
#             dsets.append(f"{_q(a.modify_by)} = :actor_id")
#         delete_sql = f"UPDATE {qtable} SET {', '.join(dsets)} WHERE {qpk} = :id{and_active}"
#     else:
#         delete_sql = f"DELETE FROM {qtable} WHERE {qpk} = :id"

#     def build_update(provided_fields):
#         """Dynamic UPDATE that only touches the columns the client actually sent.
#         Prevents omitted columns from being nulled (ORA-01407 on NOT NULL columns).
#         Only fields in `fields` are honored; unknown keys are ignored."""
#         cols = [f"{_q(column(f))} = :{f}" for f in fields if f in provided_fields]
#         if a.modify_at:
#             cols.append(f"{_q(a.modify_at)} = SYSDATE")
#         if a.modify_by:
#             cols.append(f"{_q(a.modify_by)} = :actor_id")
#         return f"UPDATE {qtable} SET {', '.join(cols)} WHERE {qpk} = :id{and_active}"

#     return {
#         "list":   f"SELECT {select_list} FROM {qtable}{where_active} ORDER BY {qpk}",
#         "one":    f"SELECT {select_list} FROM {qtable} WHERE {qpk} = :id",
#         "insert": f"INSERT INTO {qtable} ({', '.join(icols)}) VALUES ({', '.join(ivals)}) RETURNING {qpk} INTO :new_id",
#         "update": f"UPDATE {qtable} SET {', '.join(sets)} WHERE {qpk} = :id{and_active}",
#         "build_update": build_update,
#         "delete": delete_sql,
#         "stamps_create_by": bool(a.create_by),
#         "stamps_modify_at": bool(a.modify_at),
#         "stamps_modify_by": bool(a.modify_by),
#         "soft_delete": bool(a.is_deleted),
#     }
from dataclasses import dataclass


@dataclass
class Audit:
    """Exact DB names of the audit / soft-delete columns. Oracle stores unquoted
    names UPPERCASE, so the defaults are uppercase. Set any field to None to disable
    that piece; pass audit=None to make_crud_router for a table with no audit columns."""
    is_deleted: str | None = "IS_DELETED"
    create_at: str | None = "CREATE_AT"
    create_by: str | None = "CREATE_BY"
    modify_at: str | None = "MODIFY_AT"
    modify_by: str | None = "MODIFY_BY"


_OFF = Audit(None, None, None, None, None)


def _q(name: str) -> str:
    return f'"{name}"'


def _order_by_clause(order_by, qpk: str) -> str:
    """Build a generic ORDER BY body for the list query.

    order_by: None | column name | list of column names (trusted DB identifiers,
    same trust model as table/pk/overrides). Each is quoted; the pk (already quoted,
    passed as qpk) is appended as a stable final tiebreaker unless it's already listed.
    None -> just the pk, so tables that don't opt in keep their original ordering.

    NULLs sort last by default in both Oracle and PostgreSQL, so lookup rows that have
    no value in the chosen column fall to the end.
    """
    if not order_by:
        return qpk
    cols = [order_by] if isinstance(order_by, str) else list(order_by)
    quoted = [_q(c) for c in cols]
    if qpk not in quoted:                # keep the pk as the last, deterministic key
        quoted.append(qpk)
    return ", ".join(quoted)


def plan(*, table, pk, fields, overrides=None, audit=Audit(), order_by=None):
    overrides = overrides or {}
    a = audit or _OFF

    def column(f):                      # exact DB column for a field
        return overrides.get(f, f.upper())

    qtable, qpk = _q(table), _q(pk)

    sel = [qpk]
    for f in fields:
        c = column(f)
        sel.append(_q(c) if f == c.lower() else f"{_q(c)} AS {f}")
    for c in (a.create_at, a.create_by, a.modify_at, a.modify_by):
        if c:
            sel.append(_q(c))
    select_list = ", ".join(sel)

    where_active = f" WHERE {_q(a.is_deleted)} = 'no'" if a.is_deleted else ""
    and_active = f" AND {_q(a.is_deleted)} = 'no'" if a.is_deleted else ""

    icols = [qpk] + [_q(column(f)) for f in fields]
    ivals = [f"(SELECT NVL(MAX({qpk}), 0) + 1 FROM {qtable})"] + [f":{f}" for f in fields]
    if a.is_deleted:
        icols.append(_q(a.is_deleted)); ivals.append("'no'")
    if a.create_at:
        icols.append(_q(a.create_at)); ivals.append("SYSDATE")
    if a.create_by:
        icols.append(_q(a.create_by)); ivals.append(":actor_id")

    sets = [f"{_q(column(f))} = :{f}" for f in fields]
    if a.modify_at:
        sets.append(f"{_q(a.modify_at)} = SYSDATE")
    if a.modify_by:
        sets.append(f"{_q(a.modify_by)} = :actor_id")

    if a.is_deleted:
        dsets = [f"{_q(a.is_deleted)} = 'yes'"]
        if a.modify_at:
            dsets.append(f"{_q(a.modify_at)} = SYSDATE")
        if a.modify_by:
            dsets.append(f"{_q(a.modify_by)} = :actor_id")
        delete_sql = f"UPDATE {qtable} SET {', '.join(dsets)} WHERE {qpk} = :id{and_active}"
    else:
        delete_sql = f"DELETE FROM {qtable} WHERE {qpk} = :id"

    def build_update(provided_fields):
        """Dynamic UPDATE that only touches the columns the client actually sent.
        Prevents omitted columns from being nulled (ORA-01407 on NOT NULL columns).
        Only fields in `fields` are honored; unknown keys are ignored."""
        cols = [f"{_q(column(f))} = :{f}" for f in fields if f in provided_fields]
        if a.modify_at:
            cols.append(f"{_q(a.modify_at)} = SYSDATE")
        if a.modify_by:
            cols.append(f"{_q(a.modify_by)} = :actor_id")
        return f"UPDATE {qtable} SET {', '.join(cols)} WHERE {qpk} = :id{and_active}"

    # Display order for the list. Generic: order_by may be a single column name or a
    # list of them; the pk is always the final tiebreaker (deduped if you pass it).
    # Omitted (None) -> order by the pk, so tables that don't opt in are unaffected.
    order_clause = _order_by_clause(order_by, qpk)

    return {
        "list":   f"SELECT {select_list} FROM {qtable}{where_active} ORDER BY {order_clause}",
        "one":    f"SELECT {select_list} FROM {qtable} WHERE {qpk} = :id",
        "insert": f"INSERT INTO {qtable} ({', '.join(icols)}) VALUES ({', '.join(ivals)}) RETURNING {qpk} INTO :new_id",
        "update": f"UPDATE {qtable} SET {', '.join(sets)} WHERE {qpk} = :id{and_active}",
        "build_update": build_update,
        "delete": delete_sql,
        "stamps_create_by": bool(a.create_by),
        "stamps_modify_at": bool(a.modify_at),
        "stamps_modify_by": bool(a.modify_by),
        "soft_delete": bool(a.is_deleted),
    }