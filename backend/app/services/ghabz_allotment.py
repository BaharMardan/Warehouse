# """Per-goods-code allotment arithmetic for قبض انبار.

# This module owns the rules that TRG_CHK_GHABZ_TALI_LIMIT enforces in the
# database, so the API can refuse a bad draw with a precise Persian message
# instead of letting a statement-level ORA-20001 surface.

# The trigger's contract, restated:

# * A receipt line is keyed by goods code + packaging. Packaging variants remain
#   separate, while tally rows sharing both values form one allotment.
# * For each code, the sum of NUMBER_KALA / WEIGHTE_asnad / WEIGHTE_BASKOL across
#   every receipt of the tally may not exceed the tally's own totals for that
#   CODE_GROUPE_KALA.
# * A code whose tally totals are all zero cannot be issued at all (ORA-20011).
# * The trigger's sums do not filter IS_DELETED, so a soft-deleted receipt still
#   consumes its share. The remaining figures here match that, deliberately: a
#   number the trigger disagrees with would be offered and then refused.

# Deliberately free of database and router imports so it can be tested directly.
# """

# from fastapi import HTTPException
# from pydantic import BaseModel


# MEASURES = ("number_kala", "weighte_asnad", "weighte_baskol")

# MEASURE_LABELS = {
#     "number_kala": "تعداد",
#     "weighte_asnad": "وزن اسناد",
#     "weighte_baskol": "وزن باسکول",
# }

# # receipt-side measure -> the tally-side column holding its allotment
# _TALLY_KEYS = {
#     "number_kala": "tally_number_kala",
#     "weighte_asnad": "tally_weighte",
#     "weighte_baskol": "tally_weighte_baskol",
# }

# _DESCRIPTIVE_FIELDS = (
#     "description_kala", "hscode", "type_basteh", "id_tagh_anbar", "number_hamel",
#     "source_anbar_names", "source_tagh_names",
# )


# def allotment_key(code_kala, type_basteh) -> str:
#     """Stable key for one goods-code + packaging allotment."""
#     package = "" if type_basteh is None else str(type_basteh).strip()
#     return f"{code_kala}::{package}"


# class GhabzLineInput(BaseModel):
#     """One goods code and the quantities this receipt draws for it.

#     An omitted measure means "take whatever remains" rather than zero, which is
#     what an operator issuing a final receipt expects.
#     """

#     code_kala: int
#     type_basteh: str | None = None
#     number_kala: float | None = None
#     weighte_asnad: float | None = None
#     weighte_baskol: float | None = None
#     description_kala: str | None = None
#     hscode: str | None = None
#     type_basteh: str | None = None
#     id_tagh_anbar: int | None = None
#     number_hamel: str | None = None
#     source_anbar_names: str | None = None
#     source_tagh_names: str | None = None


# class GhabzFromTallyInput(BaseModel):
#     """Omitted or empty means "draw everything still remaining on the tally"."""

#     lines: list[GhabzLineInput] | None = None


# def _number(value) -> float:
#     return 0.0 if value is None else float(value)


# def remaining(row: dict, measure: str) -> float:
#     """Raw allotment minus issued. Can be NEGATIVE.

#     Negative means the receipts already hold more than the tally now allots,
#     which happens when a tally row is deleted after receipts were issued against
#     it. It is a real data condition worth reporting, so it is not hidden here --
#     callers that need a quantity use available() instead.
#     """
#     return _number(row[_TALLY_KEYS[measure]]) - _number(row[f"issued_{measure}"])


# def available(row: dict, measure: str) -> float:
#     """What can actually be drawn: never below zero."""
#     return max(remaining(row, measure), 0.0)


# def over_issued(row: dict) -> bool:
#     """True when any measure has been issued beyond what the tally allots."""
#     return any(remaining(row, measure) < 0 for measure in MEASURES)


# def has_allotment(row: dict) -> bool:
#     """False reproduces the trigger's ORA-20011 condition: all tally totals zero."""
#     return any(_number(row[key]) != 0 for key in _TALLY_KEYS.values())


# def drawable(row: dict) -> bool:
#     """A NULL code can never be issued: it matches nothing in the trigger's
#     lookup, and a second NULL line would collide on FA_CON_تکرار_کدکلا."""
#     return (
#         row["code_kala"] is not None
#         and has_allotment(row)
#         and any(available(row, measure) > 0 for measure in MEASURES)
#     )


# def annotate(rows: list[dict]) -> list[dict]:
#     """Add the derived fields the picker needs to each allotment row.

#     remaining_* is the clamped, drawable figure, so the client can bind it
#     straight to an input's value and max without ever showing a negative.
#     over_issued flags the underlying inconsistency separately.
#     """
#     for row in rows:
#         row["allotment_key"] = allotment_key(row["code_kala"], row["type_bastem"])
#         for measure in MEASURES:
#             row[f"remaining_{measure}"] = available(row, measure)
#         row["has_allotment"] = has_allotment(row)
#         row["over_issued"] = over_issued(row)
#         row["drawable"] = drawable(row)
#     return rows


# def shared_anbar(rows: list[dict]) -> int | None:
#     """The receipt header holds one warehouse; use it only if the lines agree."""
#     warehouses = {row["id_anbar"] for row in rows if row["id_anbar"] is not None}
#     return warehouses.pop() if len(warehouses) == 1 else None


# def full_draw(row: dict) -> dict:
#     """A line taking everything still remaining for this code."""
#     return {
#         "allotment_key": row.get("allotment_key") or allotment_key(
#             row["code_kala"], row["type_bastem"]
#         ),
#         "code_kala": row["code_kala"],
#         "description_kala": row["description_kala"],
#         "hscode": row["hscode"],
#         "type_basteh": row["type_bastem"],
#         "id_tagh_anbar": row["id_tagh_anbar"],
#         "number_hamel": row["number_hamel"],
#         "source_anbar_names": row.get("source_anbar_names"),
#         "source_tagh_names": row.get("source_tagh_names"),
#         "number_kala": available(row, "number_kala"),
#         "weighte_asnad": available(row, "weighte_asnad"),
#         "weighte_baskol": available(row, "weighte_baskol"),
#     }


# def plan_lines(
#     requested: list[GhabzLineInput] | None,
#     allotments: list[dict],
#     by_key: dict,
# ) -> list[dict]:
#     """Turn the request into insertable lines, or raise a 400 explaining why not."""
#     if not requested:
#         chosen = [row for row in allotments if drawable(row)]
#         if not chosen:
#             raise HTTPException(
#                 status_code=400,
#                 detail="مقدار باقی‌مانده‌ای برای صدور قبض انبار در این تالی وجود ندارد.",
#             )
#         return [full_draw(row) for row in chosen]

#     seen: set[str] = set()
#     lines: list[dict] = []

#     for item in requested:
#         key = allotment_key(item.code_kala, item.type_basteh)
#         if key in seen:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"کد کالا {item.code_kala} بیش از یک بار در این قبض آمده است.",
#             )
#         seen.add(key)

#         row = by_key.get(key) or by_key.get(item.code_kala)
#         if row is None:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"کد کالا {item.code_kala} در این تالی وجود ندارد.",
#             )
#         if not has_allotment(row):
#             raise HTTPException(
#                 status_code=400,
#                 detail=(
#                     f"برای کد کالا {item.code_kala} هیچ مقدار مجازی در تالی ثبت نشده است."
#                 ),
#             )

#         line = full_draw(row)
#         for measure in MEASURES:
#             supplied = getattr(item, measure)
#             if supplied is None:
#                 continue
#             if supplied < 0:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"{MEASURE_LABELS[measure]} نمی‌تواند منفی باشد.",
#                 )
#             allowed = available(row, measure)
#             if supplied > allowed:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=(
#                         f"{MEASURE_LABELS[measure]} درخواستی برای کد کالا "
#                         f"{item.code_kala} ({supplied:g}) از باقی‌مانده تالی "
#                         f"({allowed:g}) بیشتر است."
#                     ),
#                 )
#             line[measure] = supplied

#         for field in _DESCRIPTIVE_FIELDS:
#             supplied = getattr(item, field)
#             if supplied is not None:
#                 line[field] = supplied

#         if all(_number(line[measure]) == 0 for measure in MEASURES):
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"برای کد کالا {item.code_kala} هیچ مقداری وارد نشده است.",
#             )
#         lines.append(line)

#     return lines

"""Per-goods-code allotment arithmetic for قبض انبار.

This module owns the rules that TRG_CHK_GHABZ_TALI_LIMIT enforces in the
database, so the API can refuse a bad draw with a precise Persian message
instead of letting a statement-level ORA-20001 surface.

The trigger's contract, restated:

* A receipt line is keyed by goods code. FA_CON_تکرار_کدکلا allows only one line
  per code per receipt, so a line is a *draw against an allotment*, never a copy
  of a tally row.
* For each code, the sum of NUMBER_KALA / WEIGHTE_asnad / WEIGHTE_BASKOL across
  every receipt of the tally may not exceed the tally's own totals for that
  CODE_GROUPE_KALA.
* A code whose tally totals are all zero cannot be issued at all (ORA-20011).
* The trigger's sums do not filter IS_DELETED, so a soft-deleted receipt still
  consumes its share. The remaining figures here match that, deliberately: a
  number the trigger disagrees with would be offered and then refused.

Deliberately free of database and router imports so it can be tested directly.
"""

from fastapi import HTTPException
from pydantic import BaseModel


MEASURES = ("number_kala", "weighte_asnad", "weighte_baskol")

MEASURE_LABELS = {
    "number_kala": "تعداد",
    "weighte_asnad": "وزن اسناد",
    "weighte_baskol": "وزن باسکول",
}

# receipt-side measure -> the tally-side column holding its allotment
_TALLY_KEYS = {
    "number_kala": "tally_number_kala",
    "weighte_asnad": "tally_weighte",
    "weighte_baskol": "tally_weighte_baskol",
}

_DESCRIPTIVE_FIELDS = (
    "description_kala", "hscode", "type_basteh", "id_tagh_anbar", "number_hamel",
)


class GhabzLineInput(BaseModel):
    """One goods code and the quantities this receipt draws for it.

    An omitted measure means "take whatever remains" rather than zero, which is
    what an operator issuing a final receipt expects.
    """

    code_kala: int
    number_kala: float | None = None
    weighte_asnad: float | None = None
    weighte_baskol: float | None = None
    description_kala: str | None = None
    hscode: str | None = None
    type_basteh: str | None = None
    id_tagh_anbar: int | None = None
    number_hamel: str | None = None


class GhabzFromTallyInput(BaseModel):
    """Omitted or empty means "draw everything still remaining on the tally"."""

    lines: list[GhabzLineInput] | None = None


def _number(value) -> float:
    return 0.0 if value is None else float(value)


def remaining(row: dict, measure: str) -> float:
    """Raw allotment minus issued. Can be NEGATIVE.

    Negative means the receipts already hold more than the tally now allots,
    which happens when a tally row is deleted after receipts were issued against
    it. It is a real data condition worth reporting, so it is not hidden here --
    callers that need a quantity use available() instead.
    """
    return _number(row[_TALLY_KEYS[measure]]) - _number(row[f"issued_{measure}"])


def available(row: dict, measure: str) -> float:
    """What can actually be drawn: never below zero."""
    return max(remaining(row, measure), 0.0)


def over_issued(row: dict) -> bool:
    """True when any measure has been issued beyond what the tally allots."""
    return any(remaining(row, measure) < 0 for measure in MEASURES)


def has_allotment(row: dict) -> bool:
    """False reproduces the trigger's ORA-20011 condition: all tally totals zero."""
    return any(_number(row[key]) != 0 for key in _TALLY_KEYS.values())


def drawable(row: dict) -> bool:
    """A NULL code can never be issued: it matches nothing in the trigger's
    lookup, and a second NULL line would collide on FA_CON_تکرار_کدکلا."""
    return (
        row["code_kala"] is not None
        and has_allotment(row)
        and any(available(row, measure) > 0 for measure in MEASURES)
    )


def annotate(rows: list[dict]) -> list[dict]:
    """Add the derived fields the picker needs to each allotment row.

    remaining_* is the clamped, drawable figure, so the client can bind it
    straight to an input's value and max without ever showing a negative.
    over_issued flags the underlying inconsistency separately.
    """
    for row in rows:
        for measure in MEASURES:
            row[f"remaining_{measure}"] = available(row, measure)
        row["has_allotment"] = has_allotment(row)
        row["over_issued"] = over_issued(row)
        row["drawable"] = drawable(row)
    return rows


def shared_anbar(rows: list[dict]) -> int | None:
    """The receipt header holds one warehouse; use it only if the lines agree."""
    warehouses = {row["id_anbar"] for row in rows if row["id_anbar"] is not None}
    return warehouses.pop() if len(warehouses) == 1 else None


def full_draw(row: dict) -> dict:
    """A line taking everything still remaining for this code."""
    return {
        "code_kala": row["code_kala"],
        "description_kala": row["description_kala"],
        "hscode": row["hscode"],
        "type_basteh": row["type_bastem"],
        "id_tagh_anbar": row["id_tagh_anbar"],
        "number_hamel": row["number_hamel"],
        "number_kala": available(row, "number_kala"),
        "weighte_asnad": available(row, "weighte_asnad"),
        "weighte_baskol": available(row, "weighte_baskol"),
    }


def master_lines(allotments: list[dict]) -> list[dict]:
    """Lines for a master receipt: the tally's full total for every goods code.

    Unlike a child receipt this ignores what has already been issued. The master
    is a picture of the whole tally, so it always carries the complete quantity
    even when children have already drawn against it. The amended trigger
    measures a master on its own, so this cannot collide with them.
    """
    chosen = [
        row for row in allotments
        if row["code_kala"] is not None and has_allotment(row)
    ]
    if not chosen:
        raise HTTPException(
            status_code=400,
            detail="این تالی هیچ کد کالای قابل صدوری ندارد.",
        )
    return [
        {
            "code_kala": row["code_kala"],
            "description_kala": row["description_kala"],
            "hscode": row["hscode"],
            "type_basteh": row["type_bastem"],
            "id_tagh_anbar": row["id_tagh_anbar"],
            "number_hamel": row["number_hamel"],
            "number_kala": _number(row["tally_number_kala"]),
            "weighte_asnad": _number(row["tally_weighte"]),
            "weighte_baskol": _number(row["tally_weighte_baskol"]),
        }
        for row in chosen
    ]


def plan_lines(
    requested: list[GhabzLineInput] | None,
    allotments: list[dict],
    by_code: dict,
) -> list[dict]:
    """Turn the request into insertable lines, or raise a 400 explaining why not."""
    if not requested:
        chosen = [row for row in allotments if drawable(row)]
        if not chosen:
            raise HTTPException(
                status_code=400,
                detail="مقدار باقی‌مانده‌ای برای صدور قبض انبار در این تالی وجود ندارد.",
            )
        return [full_draw(row) for row in chosen]

    seen: set[int] = set()
    lines: list[dict] = []

    for item in requested:
        if item.code_kala in seen:
            # Listing what arrived turns "why did this fire?" into a one-line
            # answer: either the client really sent a code twice, or it did not
            # and the fault is elsewhere.
            received = ", ".join(str(entry.code_kala) for entry in requested)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"کد کالا {item.code_kala} بیش از یک بار در این قبض آمده است. "
                    f"کدهای دریافت‌شده: [{received}]"
                ),
            )
        seen.add(item.code_kala)

        row = by_code.get(item.code_kala)
        if row is None:
            raise HTTPException(
                status_code=400,
                detail=f"کد کالا {item.code_kala} در این تالی وجود ندارد.",
            )
        if not has_allotment(row):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"برای کد کالا {item.code_kala} هیچ مقدار مجازی در تالی ثبت نشده است."
                ),
            )

        line = full_draw(row)
        for measure in MEASURES:
            supplied = getattr(item, measure)
            if supplied is None:
                continue
            if supplied < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"{MEASURE_LABELS[measure]} نمی‌تواند منفی باشد.",
                )
            allowed = available(row, measure)
            if supplied > allowed:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{MEASURE_LABELS[measure]} درخواستی برای کد کالا "
                        f"{item.code_kala} ({supplied:g}) از باقی‌مانده تالی "
                        f"({allowed:g}) بیشتر است."
                    ),
                )
            line[measure] = supplied

        for field in _DESCRIPTIVE_FIELDS:
            supplied = getattr(item, field)
            if supplied is not None:
                line[field] = supplied

        if all(_number(line[measure]) == 0 for measure in MEASURES):
            raise HTTPException(
                status_code=400,
                detail=f"برای کد کالا {item.code_kala} هیچ مقداری وارد نشده است.",
            )
        lines.append(line)

    return lines
