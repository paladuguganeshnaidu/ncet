import importlib.util
from pathlib import Path
import sqlite3

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "d1_migration_preflight.py"
SPEC = importlib.util.spec_from_file_location("d1_preflight", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_schema_preserves_constraints_but_never_exports_rows():
    with sqlite3.connect(":memory:") as source:
        source.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE);
            CREATE TABLE tasks (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id));
            CREATE INDEX task_user_idx ON tasks(user_id);
            INSERT INTO users VALUES (1, 'private-value');
        """)
        ddl = module.schema_sql(source)
    assert "private-value" not in ddl
    assert "INSERT INTO" not in ddl
    with sqlite3.connect(":memory:") as target:
        target.execute("PRAGMA foreign_keys=ON")
        target.executescript(ddl)
        assert target.execute("SELECT count(*) FROM users").fetchone()[0] == 0
        with pytest.raises(sqlite3.IntegrityError):
            target.execute("INSERT INTO tasks VALUES (1, 999)")


def test_schema_rejects_reserved_names():
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE _cf_private (id INTEGER)")
        with pytest.raises(ValueError):
            module.schema_sql(conn)


def test_schema_rejects_wide_tables():
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE wide (" + ",".join(f"c{i} TEXT" for i in range(101)) + ")")
        with pytest.raises(ValueError):
            module.schema_sql(conn)


def test_source_url_requires_postgres(monkeypatch):
    monkeypatch.setenv("NCET_SOURCE_DATABASE_URL", "sqlite:///not-production")
    with pytest.raises(ValueError):
        module.source_url()


def test_output_cannot_be_inside_repository():
    with pytest.raises(ValueError):
        module.private_destination(module.ROOT / "private.dump")
