"""Offline migration preparation only. Never writes to source PostgreSQL or remote D1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
D1_ROW_LIMIT = 2_000_000
D1_SQL_LIMIT = 100_000
D1_FREE_CAPACITY = 500_000_000


def private_destination(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError("Migration output must be outside the Git checkout")
    if not path.parent.is_dir():
        raise ValueError("Output parent must already exist")
    return path


def source_url() -> str:
    url = os.environ.get("NCET_SOURCE_DATABASE_URL", "")
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    if not url.startswith(("postgresql://", "postgres://")):
        raise ValueError("Set NCET_SOURCE_DATABASE_URL to the recovered PostgreSQL URI")
    return url


def inventory(url: str) -> dict:
    import psycopg
    from psycopg import sql

    tables = []
    with psycopg.connect(url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            cur.execute("SET LOCAL statement_timeout = '60s'")
            cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            for schema, name in cur.fetchall():
                ident = sql.Identifier(schema, name)
                cur.execute(sql.SQL("SELECT count(*) FROM {}").format(ident))
                count = cur.fetchone()[0]
                cur.execute("""
                    SELECT column_name, data_type FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema, name))
                columns = cur.fetchall()
                binary = []
                for column, dtype in columns:
                    if dtype != "bytea":
                        continue
                    field = sql.Identifier(column)
                    cur.execute(sql.SQL("""
                        SELECT count({f}), COALESCE(sum(octet_length({f})),0),
                               COALESCE(max(octet_length({f})),0),
                               count(*) FILTER (WHERE octet_length({f}) >= %s)
                        FROM {t}
                    """).format(f=field, t=ident), (D1_ROW_LIMIT,))
                    present, size, largest, oversized = cur.fetchone()
                    binary.append({"column": column, "non_null": present,
                                   "bytes": int(size), "largest_bytes": largest,
                                   "at_or_over_d1_limit": oversized})
                cur.execute("SELECT pg_total_relation_size(%s::regclass)",
                            (ident.as_string(conn),))
                tables.append({"schema": schema, "table": name, "rows": count,
                               "columns": len(columns), "postgres_relation_bytes": cur.fetchone()[0],
                               "binary_columns": binary})
            cur.execute("SELECT version_num FROM public.alembic_version ORDER BY version_num")
            revisions = [row[0] for row in cur.fetchall()]
        conn.rollback()
    return {"alembic_revisions": revisions, "tables": tables,
            "postgres_relation_bytes": sum(t["postgres_relation_bytes"] for t in tables),
            "d1_free_capacity_bytes": D1_FREE_CAPACITY,
            "requires_object_storage_review": any(b["non_null"] for t in tables for b in t["binary_columns"]),
            "note": "PostgreSQL sizes are estimates, not D1 size forecasts; inventory contains counts, not record contents."}


def schema_sql(conn: sqlite3.Connection) -> str:
    """Extract DDL only; never export application rows or mark migrations applied."""
    entries = conn.execute("""
        SELECT type, name, sql FROM sqlite_schema
        WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
        ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1
                           WHEN 'view' THEN 2 ELSE 3 END, name
    """).fetchall()
    if not entries:
        raise ValueError("No application schema found")
    statements = []
    for kind, name, ddl in entries:
        if name.startswith("_cf_"):
            raise ValueError("Reserved Cloudflare table name")
        if kind == "table":
            column_count = conn.execute(
                "SELECT count(*) FROM pragma_table_info(?)", (name,)
            ).fetchone()[0]
            if column_count > 100:
                raise ValueError("Table exceeds D1 column limit: " + name)
        if len(ddl.encode("utf-8")) >= D1_SQL_LIMIT:
            raise ValueError("DDL exceeds D1 statement limit: " + name)
        statements.append(ddl.rstrip(";") + ";")
    return "\n\n".join(statements) + "\n"


def generate_schema(output: Path) -> None:
    output = private_destination(output)
    if output.exists():
        raise FileExistsError("Refusing to overwrite schema output")
    with tempfile.TemporaryDirectory(prefix="ncet-schema-") as tmp:
        dbfile = Path(tmp) / "schema.sqlite3"
        env = os.environ.copy()
        env.pop("NCET_SOURCE_DATABASE_URL", None)
        env["DATABASE_URL"] = "sqlite:///" + dbfile.as_posix()
        env["APP_ENV"] = "development"
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                       cwd=ROOT, env=env, check=True)
        with sqlite3.connect(dbfile) as conn:
            ddl = schema_sql(conn)
        with sqlite3.connect(":memory:") as check:
            check.execute("PRAGMA foreign_keys=ON")
            check.executescript(ddl)
            if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Generated schema failed local integrity check")
    with output.open("x", encoding="utf-8") as f:
        f.write(ddl)


def backup(url: str, root: Path) -> dict:
    """Make a native PostgreSQL archive, never an incomplete D1 replacement."""
    from psycopg.conninfo import conninfo_to_dict

    root = root.expanduser().resolve()
    if root == ROOT or ROOT in root.parents or not root.is_dir():
        raise ValueError("Backup directory must exist outside the Git checkout")
    mapping = {"host": "PGHOST", "port": "PGPORT", "dbname": "PGDATABASE",
               "user": "PGUSER", "password": "PGPASSWORD", "sslmode": "PGSSLMODE",
               "sslrootcert": "PGSSLROOTCERT", "sslcert": "PGSSLCERT",
               "sslkey": "PGSSLKEY", "connect_timeout": "PGCONNECT_TIMEOUT",
               "application_name": "PGAPPNAME", "options": "PGOPTIONS",
               "target_session_attrs": "PGTARGETSESSIONATTRS"}
    params = conninfo_to_dict(url)
    if set(params) - set(mapping):
        raise ValueError("Unsupported URI options; use a reviewed libpq backup workflow")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("PG") and k != "NCET_SOURCE_DATABASE_URL"}
    env.update({mapping[k]: v for k, v in params.items()})
    env.setdefault("PGCONNECT_TIMEOUT", "10")
    directory = Path(tempfile.mkdtemp(prefix="ncet-recovery-", dir=root))
    partial = directory / "source.dump.partial"
    complete = directory / "source.dump"
    subprocess.run(["pg_dump", "--format=custom", "--no-password", "--file", str(partial)],
                   env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pg_restore", "--list", str(partial)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    partial.rename(complete)
    with complete.open("rb") as f:
        checksum = hashlib.file_digest(f, "sha256").hexdigest()
    return {"backup": str(complete), "bytes": complete.stat().st_size,
            "sha256": checksum, "catalog_verified": True,
            "restore_test": "required before cutover"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory", help="Read-only source inventory")
    schema = sub.add_parser("schema", help="Generate and validate local D1 candidate DDL")
    schema.add_argument("output", type=Path)
    dump = sub.add_parser("backup", help="Create private native PostgreSQL archive")
    dump.add_argument("directory", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.command == "schema":
            generate_schema(args.output)
            print("Candidate DDL generated and checked locally; no remote changes.")
        elif args.command == "inventory":
            print(json.dumps(inventory(source_url()), indent=2))
        else:
            print(json.dumps(backup(source_url(), args.directory), indent=2))
        return 0
    except Exception as exc:
        # Never echo driver exception messages which may contain connection secrets.
        print("Migration preparation stopped: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
