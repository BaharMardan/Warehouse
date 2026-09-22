"""Create the carrier-type base-data category and seed the legacy options.

The tally used to keep these values in a frontend constant.  This migration
puts the same values in FA_SYS_TERMS so base-data editors can add/update them.
It is safe to run repeatedly.
"""
from app.core.db import get_connection

CATEGORY_ID = 5
CATEGORY_TITLE = "نوع حامل"
VALUES = [
    "۴۰ فوت", "۲۰ فوت", "تریلی چادری", "تریلی یخچال‌دار",
    "کامیون جفت", "خاور", "وانت", "کمرشکن",
]


def main() -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            '''SELECT COUNT(*) FROM "FA_SYS_TERM_CATEGORIES"
               WHERE "SYS_TERM_CATEGORY_ID" = :id''',
            {"id": CATEGORY_ID},
        )
        if cur.fetchone()[0] == 0:
            cur.execute(
                '''INSERT INTO "FA_SYS_TERM_CATEGORIES"
                   ("SYS_TERM_CATEGORY_ID", "SYS_TERM_CATEGORY_TITLE",
                    "SYS_TERM_CATEGORY_STATUS", "SYS_TERM_CATEGORY_IS_DELETED")
                   VALUES (:id, :title, 'active', 'no')''',
                {"id": CATEGORY_ID, "title": CATEGORY_TITLE},
            )

        for order_no, value in enumerate(VALUES, 1):
            cur.execute(
                '''SELECT COUNT(*) FROM "FA_SYS_TERMS"
                   WHERE "SYS_TERM_CATEGORY_ID" = :category_id
                     AND "SYS_TERM_VALUE" = :value
                     AND "SYS_TERM_IS_DELETED" = 'no' ''',
                {"category_id": CATEGORY_ID, "value": value},
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    '''INSERT INTO "FA_SYS_TERMS"
                       ("SYS_TERM_CATEGORY_ID", "SYS_TERM_VALUE", "SYS_TERM_STATUS",
                        "SYS_TERM_IS_DELETED", "SYS_TERM_ORDER")
                       VALUES (:category_id, :value, 'active', 'no', :order_no)''',
                    {"category_id": CATEGORY_ID, "value": value, "order_no": order_no},
                )
        conn.commit()
        print(f"OK: ensured carrier type category {CATEGORY_ID} and {len(VALUES)} values")


if __name__ == "__main__":
    main()
