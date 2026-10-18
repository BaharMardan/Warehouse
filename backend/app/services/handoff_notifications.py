"""Append using the caller's transaction, after all document locks/writes.

The singleton clock locks writers until commit. Unlike an Oracle sequence,
a later committed event cannot overtake an earlier uncommitted event and
make a polling client skip it. Never commit or acquire another document
lock after calling record().
"""
from typing import Literal

Target = Literal["keeper", "operator"]


def record(cursor, target: Target, tally_id: int, actor_id: int, receipt_id: int | None = None):
    if target not in ("keeper", "operator"):
        raise ValueError("Invalid handoff target")
    event_id = cursor.var(int)
    cursor.execute("""
        UPDATE "FA_HANDOFF_CLOCK" SET "VERSION" = "VERSION" + 1
        WHERE "ID" = 1 RETURNING "VERSION" INTO :event_id
    """, {"event_id": event_id})
    cursor.execute("""
        INSERT INTO "FA_HANDOFF_EVENTS" ("ID", "TARGET", "TALLY_ID", "RECEIPT_ID", "ACTOR_ID")
        VALUES (:id, :target, :tally_id, :receipt_id, :actor_id)
    """, {"id": int(event_id.getvalue()[0]), "target": target,
          "tally_id": tally_id, "receipt_id": receipt_id, "actor_id": actor_id})


def targets_for(permissions):
    targets = []
    if "tally.services" in permissions:
        targets.append("keeper")
    if "tally.edit" in permissions or "ghabz.issue" in permissions:
        targets.append("operator")
    return targets


def read(cursor, after: int | None, targets, actor_id: int):
    # One SQL statement gives the clock and event counts the same Oracle snapshot.
    # No document status/deletion filter: a later transition cannot erase an alert.
    cursor.execute("""
        SELECT c."VERSION",
          (SELECT COUNT(*) FROM "FA_HANDOFF_EVENTS" e
           WHERE e."ID" > :after AND e."ID" <= c."VERSION"
             AND e."TARGET" = 'keeper' AND :keeper = 1 AND e."ACTOR_ID" <> :actor),
          (SELECT COUNT(*) FROM "FA_HANDOFF_EVENTS" e
           WHERE e."ID" > :after AND e."ID" <= c."VERSION"
             AND e."TARGET" = 'operator' AND :operator = 1 AND e."ACTOR_ID" <> :actor)
        FROM "FA_HANDOFF_CLOCK" c WHERE c."ID" = 1
    """, {"after": after, "keeper": int("keeper" in targets),
          "operator": int("operator" in targets), "actor": actor_id})
    version, keeper, operator = cursor.fetchone()
    # String cursors preserve NUMBER(19) precision in JavaScript.
    return {"cursor": str(version), "keeper": int(keeper), "operator": int(operator)}
