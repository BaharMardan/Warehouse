"""Create shared base-data display ordering. Safe to rerun; existing orders stay intact."""
from app.core.db import get_connection
from app.crud.registry import crud_routers


def main():
    prefixes = [router.prefix for router in crud_routers
                if any(route.path.endswith("/display-order") for route in router.routes)]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'FA_DISPLAY_ORDER'")
            if not cur.fetchone()[0]:
                cur.execute('CREATE TABLE "FA_DISPLAY_ORDER" ('
                            '"RESOURCE" VARCHAR2(200) PRIMARY KEY, "ORDER_JSON" CLOB NOT NULL, '
                            '"UPDATED_BY" NUMBER, "UPDATED_AT" TIMESTAMP)')
            for prefix in prefixes:
                cur.execute('MERGE INTO "FA_DISPLAY_ORDER" d USING (SELECT :scope_key AS scope_key FROM DUAL) s '
                            'ON (d."RESOURCE" = s.scope_key) WHEN NOT MATCHED THEN '
                            'INSERT ("RESOURCE", "ORDER_JSON") VALUES (s.scope_key, :ordering)',
                            {"scope_key": prefix, "ordering": "[]"})
        conn.commit()
    print(f"Shared display ordering ready for {len(prefixes)} lookup resources")


if __name__ == "__main__":
    main()
