"""The worklist only links to issued invoices, and the APEX-era tally preview
endpoint is gone (invoices are priced only by the 1405 rules)."""
from app.main import app
from app.routers import kartabl


def test_tally_preview_endpoint_is_removed():
    paths = set(app.openapi()["paths"])   # works however the routers are wrapped
    assert "/invoice/from-tally/{tali_id}/preview" not in paths
    assert "/invoice/{invoice_id}" in paths and "/invoice/list" in paths


def test_kartabl_lists_every_issued_invoice_of_a_tally():
    sql = kartabl.LIST_SQL
    assert "AS invoices" in sql
    assert '"FA_SORAT_HESAB_HEADER" s' in sql and "\'no\'" in sql
