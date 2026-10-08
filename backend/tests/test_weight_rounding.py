"""Whole-ton billing boundaries, including the production SQL expressions."""
import ast
import math
import re
import sqlite3
from pathlib import Path

import pytest
from app.services.container_excess import excess_tons
from app.services.storage_calc import storage_charge, location


@pytest.mark.parametrize("kg,tons", [(1, 1), (15000, 15), (15001, 16), (15100, 16)])
def test_storage_bills_whole_tons(kg, tons):
    charge = storage_charge("weight", rate=100, loc=location("1"), days=1, weight_kg=kg)
    assert charge.amount == tons * 100


@pytest.mark.parametrize("code,kg,tons", [("201", 9999, 0), ("201", 10000, 0),
    ("201", 10001, 1), ("201", 15100, 6), ("401", 15000, 0), ("401", 15100, 1)])
def test_excess_bills_whole_tons(code, kg, tons):
    assert excess_tons(code, kg) == tons


@pytest.mark.parametrize("router", ["receipt_workflow", "tally"])
@pytest.mark.parametrize("kind", ["loading", "unloading"])
def test_handling_sql_rounds_each_goods_line(router, kind):
    source = Path(__file__).parents[1] / "app" / "routers" / (router + ".py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    sql = next(ast.literal_eval(node.value) for node in tree.body
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "STRIP_SQL" for t in node.targets))
    expressions = re.findall(r'\(SELECT (SUM[\s\S]*?)\s+FROM "FA_TALI_DETAILES"', sql)
    assert len(expressions) == (2 if router == "receipt_workflow" else 1)
    expression = expressions[(kind == "loading") if router == "receipt_workflow" else 0]
    expression = expression.replace('j."pricing_type"', "'" + kind + "'")
    with sqlite3.connect(":memory:") as db:
        db.create_function("NVL", 2, lambda value, default: default if value is None else value)
        db.create_function("CEIL", 1, math.ceil)
        # Real-valued weights preserve Oracle's division semantics in SQLite.
        db.execute('CREATE TABLE goods (WEIGHTE REAL, price_loading REAL, price_unloding REAL)')
        db.executemany('INSERT INTO goods VALUES (?, 100, 200)', [(15100,), (15000,), (1,), (None,)])
        amount = db.execute('SELECT ' + expression.replace('p.', 'd.') + ' FROM goods d').fetchone()[0]
    assert amount == 32 * (100 if kind == "loading" else 200)
