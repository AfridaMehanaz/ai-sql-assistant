"""Unit tests for the SQL safety guard + schema loading. No API key needed.

Run:  pytest tests/ -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import build_db   # noqa: E402
import agent       # noqa: E402


def setup_module(_):
    build_db.build()


def test_simple_select_allowed():
    assert agent.is_safe("SELECT * FROM customers")


def test_select_with_join_allowed():
    assert agent.is_safe(
        "SELECT c.name, l.principal FROM customers c JOIN loans l "
        "ON c.customer_id = l.customer_id WHERE l.status = 'default'"
    )


def test_insert_blocked():
    assert not agent.is_safe("INSERT INTO customers VALUES (99,'x','y','z','2020-01-01',700)")


def test_delete_blocked():
    assert not agent.is_safe("DELETE FROM loans")


def test_drop_blocked():
    assert not agent.is_safe("DROP TABLE customers")


def test_update_blocked():
    assert not agent.is_safe("UPDATE accounts SET balance = 0")


def test_stacked_statement_blocked():
    assert not agent.is_safe("SELECT 1; DROP TABLE customers")


def test_non_select_blocked():
    assert not agent.is_safe("PRAGMA table_info(customers)")


def test_db_is_read_only():
    import pytest
    with pytest.raises(Exception):
        agent.run_sql("INSERT INTO customers VALUES (99,'x','y','z','2020-01-01',700)")


def test_schema_has_all_tables():
    schema = agent.get_schema()
    for t in ("customers", "accounts", "transactions", "loans", "payments"):
        assert t in schema
