import threading

import duckdb
import pandas as pd
from sqlalchemy import text

from . import catalog
from .db import get_engine

lock = threading.RLock()

_db: duckdb.DuckDBPyConnection | None = None
_datasets: dict[str, dict] = {}


def reload_cache() -> dict:
    """
    Refresh the in-memory, sandboxed DuckDB copy of every table listed in the
    Supabase catalog. This is what execute_query/get_schema/get_data_profile
    actually read from -- Postgres is the source of truth, DuckDB is a
    read-only, network-isolated working copy.
    """
    global _db, _datasets

    entries = catalog.list_catalog()

    new_db = duckdb.connect(
        database=":memory:",
        config={
            "enable_external_access": "false",
            "threads": "2",
            "memory_limit": "512MB",
        },
    )

    new_datasets = {}
    errors = []

    engine = get_engine()

    with engine.begin() as conn:
        for entry in entries:
            table_name = entry["table_name"]

            try:
                frame = pd.read_sql_query(text(f'select * from "{table_name}"'), conn)
            except Exception as error:
                errors.append({"table": table_name, "error": str(error)})
                continue

            new_db.register("_loading_frame", frame)
            new_db.execute(
                f'create table "{table_name}" as select * from "_loading_frame"'
            )
            new_db.unregister("_loading_frame")

            new_datasets[table_name] = {
                "directory": entry["directory_path"],
                "file": entry["file_name"],
                "sheet": entry["sheet_name"],
                "rows": entry["row_count"],
                "columns": [c["column"] for c in entry["column_schema"]],
            }

    with lock:
        old_db = _db
        _db = new_db
        _datasets = new_datasets

        if old_db is not None:
            old_db.close()

    return {"tables_loaded": len(new_datasets), "errors": errors}


def get_state() -> tuple[duckdb.DuckDBPyConnection, dict[str, dict]]:
    with lock:
        return _db, dict(_datasets)
