from app.routers import invoice
from app.routers import receipt_workflow
from app.services.invoice_seller import SELLER
from test_issue_invoice_flow import wired


def test_existing_invoice_uses_fixed_identity(monkeypatch):
    monkeypatch.setattr(invoice, "fetch_one", lambda *a: {"seller_name": "old", "seller_address": None, "seller_national_id": None})
    monkeypatch.setattr(invoice, "fetch_all", lambda *a: [])
    header = invoice.get_invoice(1)["header"]
    assert all(header[key] == value for key, value in SELLER.items())


def test_list_uses_fixed_seller(monkeypatch):
    monkeypatch.setattr(invoice, "fetch_all", lambda *a: [{"id_sorat": 1, "seller_name": None}])
    assert invoice.list_invoices()[0]["seller_name"] == SELLER["seller_name"]


def test_new_invoice_persists_fixed_seller(wired):
    _, _, cur = wired
    receipt_workflow.issue_invoice(1, {"id": 1}, receipt_workflow.InvoiceIssueInput(apply_deductions=False))
    sql, params = cur.execute.call_args_list[0].args
    for key, value in SELLER.items():
        assert params[key] == value
        assert ":" + key in sql
