"""Manual Oracle smoke test. All business records are rolled back."""
from contextlib import ExitStack
from unittest.mock import patch
from fastapi import HTTPException
from app.core.db import get_connection
from app.routers import ghabz, receipt_workflow as api, tally_handoff
from app.services import receipt_db as db
from app.services.ghabz_allotment import GhabzFromTallyInput
from app.services.tally_numbering import allocate_next_tally_number
from app.services.invoice_calc import SERVICE_LABELS


def must_reject(action, code=409):
    try:
        action()
    except HTTPException as exc:
        assert exc.status_code == code, exc.detail
    else:
        raise AssertionError("Invalid action was accepted")


def main():
    temporary_tallies = []
    with get_connection() as conn:
        class RollbackConnection:
            def cursor(self):
                return conn.cursor()

            def commit(self):
                pass

            def rollback(self):
                conn.rollback()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        proxy = RollbackConnection()
        try:
            with ExitStack() as patches:
                for module in (ghabz, api, db, tally_handoff):
                    patches.enter_context(patch.object(module, "get_connection", lambda: proxy))

                def run_case(cargo, parts, pallets):
                    with conn.cursor() as cur:
                        cur.execute('SELECT MIN("ID") FROM "FA_USERS"')
                        actor = int(cur.fetchone()[0])
                        # Invoices bill storage from "storage_price" (1405 rules).
                        cur.execute('''SELECT "id_kala_price" FROM "fa_kala_price"
                            WHERE "storage_price" IS NOT NULL AND "IS_DELETED" = 'no'
                            FETCH FIRST 1 ROW ONLY''')
                        rate = cur.fetchone()[0]
                        number = allocate_next_tally_number(cur)
                        out = cur.var(int)
                        cur.execute('''INSERT INTO "FA_TALI_HEADER"
                            ("TALI_NUMBER","CREATE_AT","DATE_UNLOADING","IS_DELETED",
                             "HANDOFF_STEP","IS_VOLUMETRIC","VOLUMETRIC_PALLETS")
                            VALUES (:num,SYSDATE,SYSDATE,'no','returned',:cargo,:pallets)
                            RETURNING "ID_TALI" INTO :id''',
                            {"num": number, "cargo": cargo,
                             "pallets": 100 if cargo == "volumetric" else None, "id": out})
                        tid = int(out.getvalue()[0])
                        temporary_tallies.append(tid)
                        # Container storage is billed per container, so that case needs a
                        # carrier number and (for the final checklist) its transportation answer.
                        hamel = "SMOKE-CONTAINER" if cargo == "container" else None
                        cur.execute('''INSERT INTO "FA_TALI_DETAILES"
                            ("ID_HEADERS_TALI","CODE_GROUPE_KALA","HSCODE","DESCRIPTION_KALA",
                             "NUMBER_KALA","WEIGHTE","WEIGHTE_BASKOL","ZARIB_MAHAL","NUMBER_HAMEL","IS_DELETED")
                            VALUES (:tid,:rate,'99000001','temporary checklist smoke',100,100,100,'1',:hamel,'no')
                            RETURNING "ID_TALI_DETAILS" INTO :id''', {"tid": tid, "rate": rate, "hamel": hamel, "id": out})
                        source_id = int(out.getvalue()[0])
                        if hamel:
                            cur.execute('''INSERT INTO "FA_TALI_CARRIER_TRANSPORTATION"
                                ("TALI_ID","NUMBER_HAMEL","HAS_TRANSPORTATION") VALUES (:tid,:hamel,'no')''',
                                {"tid": tid, "hamel": hamel})
                    user = {"id": actor}
                    general = ghabz.create_master_ghabz(tid, user)["id_ghabz"]
                    receipts = []
                    if parts:
                        for part in parts:
                            request = GhabzFromTallyInput(lines=[{
                                "hscode": "99000001", "number_kala": part,
                                "weighte_asnad": part, "weighte_baskol": part}])
                            rid = ghabz.create_ghabz_from_tally(tid, request, user)["id_ghabz"]
                            receipts.append(rid)
                            api.set_sources(rid, api.SourceInput(lines=[{
                                "tally_detail_id": source_id, "quantity": part, "weight": part, "baskol": part}]))
                        assert not api.get_workflow(general)["show_checklist"]
                        assert not api.get_workflow(general)["show_invoice"]
                        must_reject(lambda: api.finalize(general, user))
                    else:
                        receipts = [general]
                    handoff = tally_handoff.get_handoff(tid)
                    assert handoff["can_edit_services"] and handoff["step"] == "keeper"
                    tally_handoff.save_volumetric(tid, tally_handoff.CargoTypeInput(
                        cargo_type=cargo, volumetric_pallets=100 if cargo == "volumetric" else None), user)
                    if pallets:
                        for rid, quantity in zip(receipts, pallets):
                            ghabz.update_ghabz_extras(rid, ghabz.GhabzExtrasInput(pallet_quantity=quantity), user)
                    with conn.cursor() as cur:
                        db.guard_services(cur, tid)
                        out = cur.var(int)
                        cur.execute('''INSERT INTO "fa_kala_other_service" ("code","title","price","IS_DELETED")
                            VALUES ('checklist-smoke','temporary checklist smoke','1000','no')
                            RETURNING "id_kala_other_service" INTO :id''', {"id": out})
                        catalog_id = int(out.getvalue()[0])
                        cur.execute('''INSERT INTO "fa_tali_kala_other_service"
                            ("tali_id","kala_other_service_id","NUMBER_SERVICE","IS_DELETED")
                            VALUES (:tid,:sid,1,'no')''', {"tid": tid, "sid": catalog_id})
                    queued = {r["id"] for r in api.keeper_queue()}
                    assert set(receipts).issubset(queued)
                    if parts:
                        assert general not in queued
                    must_reject(lambda: api.issue_invoice(receipts[0], user))
                    amounts = []
                    for index, rid in enumerate(receipts):
                        api.finalize(rid, user)
                        assert api.get_workflow(rid)["can_invoice"]
                        with conn.cursor() as cur:
                            must_reject(lambda: db.guard_services(cur, tid))
                        if cargo == "volumetric":
                            must_reject(lambda: ghabz.update_ghabz_extras(
                                rid, ghabz.GhabzExtrasInput(pallet_quantity=1), user))
                        issued = api.issue_invoice(rid, user)
                        assert api.issue_invoice(rid, user) == issued
                        with conn.cursor() as cur:
                            cur.execute('''SELECT "PRICE_DETAILS" FROM "FA_SORA_HESAB_DETAILS"
                                WHERE "ID_SORA_HEADER"=:id AND "DESCRIPTION"=:label''',
                                {"id": issued["invoice_id"], "label": SERVICE_LABELS["other_service"]})
                            amounts.append(cur.fetchone()[0])
                            # Catalog changes between siblings cannot change the frozen pool.
                            cur.execute("""UPDATE "fa_kala_other_service" SET "price"='2000' WHERE "id_kala_other_service"=:id""",
                                        {"id": catalog_id})
                    expected = [1000] if not parts else [300, 700]
                    assert amounts == expected, (cargo, amounts)
                    assert all(not r["id"] in receipts for r in api.keeper_queue())
                    print(cargo, "general" if not parts else "detailed", "PASS:", amounts)

                run_case("weight", None, None)
                run_case("weight", [30, 70], None)
                run_case("volumetric", [90, 10], [30, 70])
                run_case("container", [30, 70], None)
        finally:
            conn.rollback()
        with conn.cursor() as cur:
            for tid in temporary_tallies:
                cur.execute('SELECT COUNT(*) FROM "FA_TALI_HEADER" WHERE "ID_TALI"=:id', {"id": tid})
                assert cur.fetchone()[0] == 0
        print("All temporary tally, receipt, service and invoice records rolled back")


if __name__ == "__main__":
    main()
