from decimal import Decimal
from datetime import date
from app.services import income_report as report
from app.routers import reports as api


def row(owner, invoice, amount, kind="storage", **extra):
    return {"owner_id": owner, "owner_name": "Same name", "invoice_id": invoice,
            "amount": amount, "row_kind": kind, **extra}


def test_owners_with_same_name_are_distinct_and_invoices_are_counted_once():
    groups = report.summarize_owners([row(1,10,100),row(1,10,20,"tax"),row(2,11,50)])
    assert len(groups)==2
    assert groups[0]["invoice_count"]==1
    assert groups[0]["net"]==100 and groups[0]["payable"]==120


def test_owner_totals_preserve_discounts_prepayments_and_supplementary_income():
    rows=[row(1,10,100),row(1,10,-10,"discount"),row(1,10,9,"tax"),row(1,10,-20,"prepayment"),
          row(1,11,50,original_invoice_id=10),row(2,12,40)]
    groups=report.summarize_owners(rows)
    assert groups[0]["invoice_count"]==2
    for key,value in report.summarize(rows)["summary"].items():
        assert sum(group[key] for group in groups)==value


def test_unknown_owner_and_cancelled_only_owner_are_included():
    groups=report.summarize_owners([row(None,10,20)], [row(3,11,50)])
    assert {group["owner_id"] for group in groups}=={0,3}
    assert report.filter_owner([row(None,10,20),row(1,11,40)],0)[0]["invoice_id"]==10
    assert next(group for group in groups if group["owner_id"]==3)["net"]==0


def test_summary_and_detail_apply_same_owner_filter(monkeypatch):
    period=(date(2026,1,1),date(2026,1,31))
    monkeypatch.setattr(api,"income_rows",lambda period:[row(1,10,100),row(2,11,50)])
    monkeypatch.setattr(api,"cancelled_rows",lambda period:[row(1,12,20),row(2,13,30)])
    summary=api.income_summary(period,{"id":1},owner_id=1)
    lines=api.income_lines(period,None,{"id":1},owner_id=1)
    assert summary["summary"]["net"]==lines["total"]==100
    assert summary["cancelled"]["count"]==1
    assert len(summary["owners"])==2
    assert all(line["owner_id"]==1 for line in lines["lines"])
