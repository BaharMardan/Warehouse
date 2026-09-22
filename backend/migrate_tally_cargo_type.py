"""Migrate the keeper handoff answer from yes/no to weight/volumetric/container."""
from app.core.db import get_connection


def main() -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        # Drop the old checks first. Otherwise changing yes -> volumetric while
        # a pallet count is present violates the old yes/no constraint.
        for name in ("CK_FA_TALI_VOLUMETRIC_PALLETS", "CK_FA_TALI_IS_VOLUMETRIC"):
            try:
                cur.execute(f'ALTER TABLE "FA_TALI_HEADER" DROP CONSTRAINT "{name}"')
            except Exception as exc:
                if "ORA-02443" not in str(exc):
                    raise
        try:
            cur.execute('ALTER TABLE "FA_TALI_HEADER" MODIFY ("IS_VOLUMETRIC" VARCHAR2(12 CHAR))')
        except Exception as exc:
            if "ORA-01442" not in str(exc):
                raise
        # Existing yes/no rows are preserved semantically: yes was volumetric;
        # no is treated as weight until a keeper revisits the tally.
        cur.execute('UPDATE "FA_TALI_HEADER" SET "IS_VOLUMETRIC" = \'volumetric\' WHERE "IS_VOLUMETRIC" = \'yes\'')
        cur.execute('UPDATE "FA_TALI_HEADER" SET "IS_VOLUMETRIC" = \'weight\' WHERE "IS_VOLUMETRIC" = \'no\'')
        cur.execute('ALTER TABLE "FA_TALI_HEADER" ADD CONSTRAINT "CK_FA_TALI_IS_VOLUMETRIC" CHECK ("IS_VOLUMETRIC" IN (\'weight\', \'volumetric\', \'container\')) ENABLE')
        cur.execute('ALTER TABLE "FA_TALI_HEADER" ADD CONSTRAINT "CK_FA_TALI_VOLUMETRIC_PALLETS" CHECK ("VOLUMETRIC_PALLETS" IS NULL OR ("IS_VOLUMETRIC" = \'volumetric\' AND "VOLUMETRIC_PALLETS" >= 1 AND "VOLUMETRIC_PALLETS" = TRUNC("VOLUMETRIC_PALLETS"))) ENABLE')
        conn.commit()
        print("OK: tally handoff cargo types migrated")


if __name__ == "__main__":
    main()
