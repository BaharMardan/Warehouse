"""Operator / warehouse-keeper handoff on a tally, as pure rules.

A tally moves through three steps, stored in FA_TALI_HEADER.HANDOFF_STEP:

    operator   the operator fills the header and goods rows, then sends it on
    keeper     the warehouse keeper answers «آیا کالا حجمی است؟», completes the
               five service sections and sends it back
    returned   receipts can be issued

No database or FastAPI imports, so these rules are unit-tested without Oracle
(tests/test_tally_handoff.py). Each *_error function returns a Persian message
for the user, or None when the action is allowed.
"""

OPERATOR = "operator"
KEEPER = "keeper"
RETURNED = "returned"
STEPS = (OPERATOR, KEEPER, RETURNED)

YES = "yes"
NO = "no"
MAX_PALLETS = 100_000

_NOT_WITH_OPERATOR = {
    KEEPER: "این تالی قبلاً برای انباردار ارسال شده است",
    RETURNED: "انباردار این تالی را تکمیل کرده و به اپراتور برگردانده است",
}
_NOT_WITH_KEEPER = {
    OPERATOR: "این تالی هنوز برای انباردار ارسال نشده است",
    RETURNED: "این تالی قبلاً به اپراتور برگردانده شده است",
}


def send_to_keeper_error(step: str, goods_rows: int) -> str | None:
    if step != OPERATOR:
        return _NOT_WITH_OPERATOR.get(step, "وضعیت تالی نامعتبر است")
    if goods_rows < 1:
        return "ابتدا دست‌کم یک ردیف کالا ثبت کنید"
    return None


def volumetric_error(step: str, is_volumetric: str, pallets: int | None) -> str | None:
    """The keeper's answer may be saved, and changed, only while the tally is with them.

    «بله» may be saved before the pallet count is typed; «خیر» never carries one.
    """
    if step != KEEPER:
        return _NOT_WITH_KEEPER.get(step, "وضعیت تالی نامعتبر است")
    if is_volumetric not in (YES, NO):
        return "پاسخ «آیا کالا حجمی است؟» باید بله یا خیر باشد"
    if is_volumetric == NO and pallets is not None:
        return "برای کالای غیرحجمی تعداد پالت ثبت نمی‌شود"
    if pallets is not None and not 1 <= pallets <= MAX_PALLETS:
        return "تعداد پالت باید عددی صحیح و دست‌کم ۱ باشد"
    return None


def return_to_operator_error(step: str, is_volumetric: str | None, pallets: int | None) -> str | None:
    if step != KEEPER:
        return _NOT_WITH_KEEPER.get(step, "وضعیت تالی نامعتبر است")
    if is_volumetric not in (YES, NO):
        return "ابتدا به پرسش «آیا کالا حجمی است؟» پاسخ دهید"
    if is_volumetric == YES and not pallets:
        return "برای کالای حجمی تعداد پالت را وارد کنید"
    return None


def issue_receipt_error(step: str | None) -> str | None:
    if step != RETURNED:
        return "تا انباردار تالی را تکمیل و به اپراتور برنگرداند، قبض انبار صادر نمی‌شود"
    return None
