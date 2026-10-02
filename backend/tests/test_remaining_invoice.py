from decimal import Decimal
from uuid import uuid4
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.services.remaining_invoice import RemainingInput, RemainingIssue, calculate
from app.routers import remaining_invoice as api
from app.routers import invoice as invoice_api
from app.services import receipt_db as db
from app.services.jalali import from_jalali


def payload(**changes):
    return RemainingInput(**{ "days": 60, "source_id": 1, "hscode": "39021030", "kala_code": "120",
        "amount": "20400", "insurance_percent": "10", **changes })


def calc(**changes):
    args = dict(payload=payload(), source={"id": 1, "description": "goods", "zarib_mahal": "بارانداز"},
        tariff={"kala_code": "120", "storage_price": 1906300, "excess_storage_price": 160930},
        cargo="container",
        settings={"system_service_rate": 100, "tax_rate": 10}, original_id=42,
        original_insurance=100, receipt_id=858, tally_id=1523)
    return calculate(**{**args, **changes})


def test_container_remaining_with_original_insurance_percentage_and_no_deductions():
    result = calc()
    assert result["snapshot"]["billed_days"] == 60
    assert [row["kind"] for row in result["rows"]] == ["system", "storage", "insurance", "tax"]
    assert [Decimal(row["price"]) for row in result["rows"]] == [100, 206775360, 10, 20677547]
    assert Decimal(result["total"]) == 227453017
    assert all(row["note"] for row in result["rows"])
    assert result["snapshot"]["inputs"]["insurance_percent"] == "10"


@pytest.mark.parametrize("cargo,amount,expected", [("weight", "2500", 9000), ("volumetric", "5", 21600)])
def test_weight_and_pallets_reuse_storage_rules(cargo, amount, expected):
    result = calc(cargo=cargo, payload=payload(amount=amount, days=30),
        tariff={"kala_code": "101", "storage_price": 100})
    assert Decimal(result["rows"][1]["price"]) == expected
    assert result["snapshot"]["billed_days"] == 30


@pytest.mark.parametrize("changes", [{"amount": 0}, {"amount": -1}, {"amount": "NaN"},
    {"insurance_percent": -1}, {"insurance_percent": 101}, {"insurance_percent": "Infinity"},
    {"hscode": ""}, {"source_id": 0}])
def test_invalid_inputs_rejected(changes):
    with pytest.raises(ValidationError):
        payload(**changes)


def test_no_original_insurance_means_zero_remaining_insurance():
    assert Decimal(calc(original_insurance=0)["rows"][2]["price"]) == 0


def test_preview_hash_changes_with_inputs_tariffs_or_entered_days():
    baseline = calc()["preview_hash"]
    assert calc()["preview_hash"] == baseline
    assert calc(payload=payload(insurance_percent=11))["preview_hash"] != baseline
    assert calc(payload=payload(days=7))["preview_hash"] != baseline
    assert calc(settings={"system_service_rate": 200, "tax_rate": 10})["preview_hash"] != baseline


@pytest.fixture
def wired(monkeypatch):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    cur.lastrowid = "test-rowid"
    cur.fetchone.return_value = (900,)
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    monkeypatch.setattr(db, "receipt", lambda *a, **k: ({"id": 858, "tally_id": 1523}, [], {}))
    monkeypatch.setattr(db, "one", lambda *a, **k: None)
    monkeypatch.setattr(api, "preview", lambda *a: calc())
    request = RemainingIssue(**payload().model_dump(), preview_hash=calc()["preview_hash"], request_id=uuid4())
    return conn, cur, request


def test_issue_stores_snapshot_and_keeps_receipt_state(wired):
    conn, cur, request = wired
    assert api.issue_invoice(858, request, {"id": 1}) == {"invoice_id": 900}
    conn.commit.assert_called_once()
    sqls = [call.args[0] for call in cur.execute.call_args_list]
    assert not any('UPDATE "fa_ghabz_anbar_header"' in sql for sql in sqls)
    assert 'INSERT INTO "FA_REMAINING_INVOICE"' in sqls[-1]
    snapshot = cur.execute.call_args.args[1]
    assert snapshot["original_id"] == 42 and snapshot["rid"] == 858
    assert '39021030' in snapshot["snapshot"]
    rows = cur.executemany.call_args.args[1]
    assert [row["kind"] for row in rows] == ["system", "storage", "insurance", "tax"]


def test_stale_preview_cannot_issue(wired):
    conn, cur, request = wired
    request.preview_hash = '0' * 64
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(858, request, {"id": 1})
    assert exc.value.status_code == 409
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()


def test_retry_does_not_create_duplicate(wired, monkeypatch):
    conn, cur, request = wired
    monkeypatch.setattr(db, "one", lambda *a, **k: {"id": 900, "receipt_id": 858,
        "preview_hash": request.preview_hash, "deleted": "no"})
    assert api.issue_invoice(858, request, {"id": 1}) == {"invoice_id": 900}
    cur.execute.assert_not_called()


def test_failure_rolls_back_header_and_details(wired):
    conn, cur, request = wired
    cur.executemany.side_effect = RuntimeError('write failed')
    with pytest.raises(RuntimeError):
        api.issue_invoice(858, request, {"id": 1})
    conn.commit.assert_not_called()


def test_missing_main_invoice_rejected(monkeypatch):
    monkeypatch.setattr(db, "rows", lambda *a, **k: [])
    with pytest.raises(HTTPException) as exc:
        api.original(None, 858)
    assert exc.value.status_code == 409


def test_goods_from_another_tally_rejected(monkeypatch):
    monkeypatch.setattr(api, "original", lambda *a: 42)
    monkeypatch.setattr(db, "rows", lambda *a, **k: [{"id": 2}])
    with pytest.raises(HTTPException) as exc:
        api.preview(None, {"id": 858, "tally_id": 1523}, {}, payload())
    assert exc.value.status_code == 422


def test_parent_with_active_remaining_invoice_cannot_be_cancelled(monkeypatch):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(invoice_api, "get_connection", lambda: conn)
    monkeypatch.setattr(db, "one", MagicMock(side_effect=[{"tally_id": 1523}, {},
        {"ghabz_id": 858, "remaining_count": 1}]))
    with pytest.raises(HTTPException) as exc:
        invoice_api.cancel_invoice(42, {"id": 1})
    assert exc.value.status_code == 409
    cur.execute.assert_not_called()


@pytest.mark.parametrize("percent,expected", [(0, 0), (10, 10), (100, 100), ("0.5", 1)])
def test_insurance_percent_and_whole_rial_rounding(percent, expected):
    assert Decimal(calc(payload=payload(insurance_percent=percent))["rows"][2]["price"]) == expected


def test_edited_hscode_and_group_code_are_frozen():
    result = calc(payload=payload(hscode="new-hs", kala_code="101"),
        tariff={"kala_code": "101", "storage_price": 10})
    assert result["snapshot"]["inputs"]["hscode"] == "new-hs"
    assert result["snapshot"]["inputs"]["kala_code"] == "101"
    assert result["snapshot"]["tariff"]["storage_price"] == 10


def test_preview_does_not_require_or_use_dates(monkeypatch):
    monkeypatch.setattr(api, "original", lambda *a: 42)
    def rows(cur, sql, params=None):
        if sql == api.GOODS_SQL:
            return [{"id": 1, "description": "goods", "zarib_mahal": "بارانداز"}]
        if sql == api.TARIFF_SQL:
            return [{"kala_code": "120", "storage_price": 1906300, "excess_storage_price": 160930}]
        if sql == api.INVOICE_SETTINGS_SQL:
            return [{"setting_key": "system_service_rate", "value_number": 100},
                    {"setting_key": "tax_rate", "value_number": 10}]
        raise AssertionError(sql)
    monkeypatch.setattr(db, "rows", rows)
    def one(cur, sql, params=None):
        assert sql == api.INSURANCE_SQL
        return {"amount": 100}
    monkeypatch.setattr(db, "one", one)
    result = api.preview(None, {"id": 858, "tally_id": 1523},
        {"is_volumetric": "container", "date_unloading": None,
         "date_cargo_exit": None}, payload(days=7))
    assert result["snapshot"]["billed_days"] == 7
    assert "end" not in result["snapshot"]


@pytest.mark.parametrize("days", [1, 7, 29, 31, 61])
@pytest.mark.parametrize("cargo,amount,daily", [("weight", "2500", "300"),
    ("volumetric", "5", "720"), ("container", "20400", "3446256")])
def test_manual_days_are_used_without_rounding(monkeypatch, days, cargo, amount, daily):
    from app.services import storage_calc as sc
    def forbidden(*args, **kwargs):
        raise AssertionError("Remaining invoices must not calculate days from dates")
    monkeypatch.setattr(sc, "billed_days", forbidden)
    tariff = ({"kala_code": "120", "storage_price": 1906300, "excess_storage_price": 160930}
              if cargo == "container" else {"kala_code": "101", "storage_price": 100})
    result = calc(payload=payload(days=days, amount=amount), cargo=cargo, tariff=tariff)
    assert Decimal(result["rows"][1]["price"]) == Decimal(daily) * days
    assert f"{days} روز" in result["rows"][1]["note"]
    assert f"{days} روز" in result["calc_note"]
    assert result["snapshot"]["inputs"]["days"] == days


@pytest.mark.parametrize("days", [0, -1, 1.5, True, None, "7"])
def test_days_must_be_a_positive_integer(days):
    with pytest.raises(ValidationError):
        payload(days=days)


def test_days_is_required():
    values = payload().model_dump()
    del values["days"]
    with pytest.raises(ValidationError):
        RemainingInput(**values)



def test_multiple_other_services_are_separate_and_taxed():
    result = calc(payload=payload(other_services=[{"service_id": 1, "quantity": 5},
        {"service_id": 2, "quantity": 10}]), service_catalog=[
        {"id": 1, "title": "برچسب", "price": 100},
        {"id": 2, "title": "پالتیزاسیون", "price": 200}])
    rows = result["rows"]
    services = [row for row in rows if row["kind"] == "service"]
    assert [row["quantity"] for row in services] == ["5", "10"]
    assert [Decimal(row["price"]) for row in services] == [500, 2000]
    assert services[0]["description"] == "سایر خدمات — برچسب"
    assert all(row["note"] for row in services)
    assert Decimal(result["total"]) == Decimal(calc()["total"]) + 2750
    assert result["snapshot"]["other_services"][1]["unit_price"] == "200"
    assert result["snapshot"]["inputs"]["other_services"][0]["quantity"] == "5"
    assert not any(row["kind"] in ("discount", "prepayment") for row in rows)


@pytest.mark.parametrize("quantity", [0, -1, "NaN", "Infinity"])
def test_invalid_service_quantity_rejected(quantity):
    with pytest.raises(ValidationError):
        payload(other_services=[{"service_id": 1, "quantity": quantity}])


@pytest.mark.parametrize("rate", [None, "bad", -1, "NaN", "Infinity"])
def test_invalid_service_rate_rejected(rate):
    with pytest.raises(ValueError):
        calc(payload=payload(other_services=[{"service_id": 1, "quantity": 1}]),
            service_catalog=[{"id": 1, "title": "service", "price": rate}])


def test_missing_service_and_changed_tariff():
    request = payload(other_services=[{"service_id": 1, "quantity": "2.5"}])
    with pytest.raises(ValueError):
        calc(payload=request)
    first = calc(payload=request, service_catalog=[{"id": 1, "title": "service", "price": 100}])
    second = calc(payload=request, service_catalog=[{"id": 1, "title": "service", "price": 200}])
    assert first["preview_hash"] != second["preview_hash"]
    assert Decimal(first["rows"][2]["price"]) == 250
