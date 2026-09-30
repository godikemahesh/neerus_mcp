
import json
import re
import threading
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import sqlglot
from sqlglot import exp
from mcp.server.fastmcp import FastMCP


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

MAX_ROWS = 200
MAX_FILE_MB = 30
MAX_QUERY_LENGTH = 10000

mcp = FastMCP("Universal Excel Analytics")

lock = threading.RLock()
db = None
datasets = {}
load_errors = []


# --------------------------------------------------
# Data loading
# --------------------------------------------------

def clean_name(name):
    """Convert an Excel sheet name to a SQL identifier."""
    name = re.sub(
        r"[^a-zA-Z0-9_]+",
        "_",
        str(name)
    ).strip("_").lower()

    if not name:
        name = "sheet"

    if name[0].isdigit():
        name = "t_" + name

    return name


def unique_columns(columns):
    """Make duplicate and empty column names unique."""
    result = []
    used = set()

    for index, column in enumerate(columns):
        base = clean_name(column)

        if not base or base == "sheet":
            base = f"column_{index + 1}"

        name = base
        suffix = 2

        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1

        used.add(name)
        result.append(name)

    return result


def json_safe(value):
    """Convert NumPy and Pandas values to JSON."""
    if isinstance(value, dict):
        return {
            str(k): json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]

    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())

    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()

    if isinstance(value, np.generic):
        return json_safe(value.item())

    if pd.isna(value):
        return None

    return value


def reload_workbooks():
    """
    Load Excel worksheets into an in-memory DuckDB.

    No Excel file is modified.
    """
    global db, datasets, load_errors

    new_db = duckdb.connect(
        database=":memory:",
        config={
            "enable_external_access": "false",
            "threads": "2",
            "memory_limit": "512MB"
        }
    )

    new_datasets = {}
    errors = []

    files = sorted(DATA_DIR.glob("*.xlsx"))

    for file in files:
        if file.name.startswith("~$"):
            continue

        try:
            if file.stat().st_size > MAX_FILE_MB * 1024 * 1024:
                raise ValueError("File exceeds size limit")

            workbook = pd.read_excel(
                file,
                sheet_name=None,
                engine="openpyxl"
            )

            for sheet_name, frame in workbook.items():
                if frame.empty:
                    continue

                frame.columns = unique_columns(
                    frame.columns
                )

                # Generate a unique SQL table name.
                base = clean_name(
                    f"{file.stem}_{sheet_name}"
                )

                table = base
                counter = 2

                while table in new_datasets:
                    table = f"{base}_{counter}"
                    counter += 1

                # Convert Pandas NaN to SQL NULL.
                new_db.register("_loading_frame", frame)

                new_db.execute(
                    f'CREATE TABLE "{table}" AS '
                    'SELECT * FROM "_loading_frame"'
                )

                new_db.unregister("_loading_frame")

                new_datasets[table] = {
                    "file": file.name,
                    "sheet": sheet_name,
                    "rows": len(frame),
                    "columns": list(frame.columns)
                }

        except Exception as error:
            errors.append({
                "file": file.name,
                "error": str(error)
            })

    with lock:
        old_db = db
        db = new_db
        datasets = new_datasets
        load_errors = errors

        if old_db is not None:
            old_db.close()

    return {
        "tables_loaded": len(new_datasets),
        "tables": new_datasets,
        "errors": errors
    }


# --------------------------------------------------
# MCP Tool 1: List datasets
# --------------------------------------------------

@mcp.tool()
def list_datasets() -> dict:
    """
    List available Excel files and worksheets.

    Call this first when discovering the user's data.
    """
    with lock:
        return {
            "datasets": datasets,
            "loading_errors": load_errors
        }


# --------------------------------------------------
# MCP Tool 2: Get schema
# --------------------------------------------------

@mcp.tool()
def get_schema(table_name: str = "") -> dict:
    """
    Get SQL table schemas and example rows.

    Leave table_name empty to inspect every table.
    """
    with lock:
        if table_name:
            if table_name not in datasets:
                return {"error": "Unknown table"}

            names = [table_name]
        else:
            names = list(datasets)

        result = {}

        for name in names:
            columns = db.execute(
                f'DESCRIBE SELECT * FROM "{name}"'
            ).fetchall()

            sample = db.execute(
                f'SELECT * FROM "{name}" LIMIT 3'
            ).df()

            result[name] = {
                "source": datasets[name],
                "schema": [
                    {
                        "column": row[0],
                        "type": row[1]
                    }
                    for row in columns
                ],
                "sample": json_safe(
                    sample.to_dict(orient="records")
                )
            }

        return result


# --------------------------------------------------
# SQL security
# --------------------------------------------------

def validate_sql(query):
    """
    Permit one read-only analytical SQL statement.

    External file access is additionally disabled
    in DuckDB.
    """
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError("SQL query is too long")

    statements = sqlglot.parse(
        query,
        read="duckdb"
    )

    if len(statements) != 1:
        raise ValueError(
            "Exactly one SQL statement is allowed"
        )

    tree = statements[0]

    if not isinstance(
        tree,
        (exp.Select, exp.Union, exp.Intersect, exp.Except)
    ):
        raise ValueError(
            "Only read-only SELECT queries are allowed"
        )

    forbidden = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Command,
        exp.Copy,
        exp.Attach,
    )

    if any(
        isinstance(node, forbidden)
        for node in tree.walk()
    ):
        raise ValueError("Unsafe SQL operation")

    # Do not permit arbitrary table-valued functions.
    for node in tree.find_all(exp.Table):
        if not isinstance(node.this, exp.Identifier):
            raise ValueError(
                "Table functions are not permitted"
            )

    # CTE names are permitted as local query tables.
    cte_names = {
        cte.alias.lower()
        for cte in tree.find_all(exp.CTE)
    }

    allowed = set(datasets) | cte_names

    for table in tree.find_all(exp.Table):
        name = table.name.lower()

        if name not in allowed:
            raise ValueError(
                f"Table is not permitted: {name}"
            )

        if table.db or table.catalog:
            raise ValueError(
                "Qualified external tables are not allowed"
            )

    # DuckDB external access is disabled, but reject
    # file-reading and other unnecessary functions too.
    blocked_functions = {
        "read_csv",
        "read_csv_auto",
        "read_json",
        "read_json_auto",
        "read_parquet",
        "sqlite_scan",
        "postgres_scan",
        "http_get",
        "query",
        "query_table",
    }

    for function in tree.find_all(exp.Func):
        name = function.sql_name().lower()

        if name in blocked_functions:
            raise ValueError(
                f"Function is not permitted: {name}"
            )

    return tree.sql(dialect="duckdb")


# --------------------------------------------------
# MCP Tool 3: Execute SQL
# --------------------------------------------------

@mcp.tool()
def execute_query(sql: str) -> dict:
    """
    Run a read-only SQL query on the loaded Excel data.

    Discover table names with list_datasets and
    column names with get_schema first.

    Supports filtering, grouping, joins, aggregations,
    window functions and date calculations.
    """
    try:
        with lock:
            safe_sql = validate_sql(sql)

            # Apply a strict output row limit.
            limited_sql = (
                "SELECT * FROM ("
                + safe_sql
                + f") AS result LIMIT {MAX_ROWS}"
            )

            result = db.execute(limited_sql).df()

            return {
                "columns": list(result.columns),
                "row_count": len(result),
                "rows": json_safe(
                    result.to_dict(orient="records")
                ),
                "limit": MAX_ROWS
            }

    except Exception as error:
        return {"error": str(error)}


# --------------------------------------------------
# MCP Tool 4: Data profiling
# --------------------------------------------------

@mcp.tool()
def get_data_profile(table_name: str) -> dict:
    """
    Analyze column types, missing values and
    descriptive statistics for an Excel table.
    """
    with lock:
        if table_name not in datasets:
            return {"error": "Unknown table"}

        frame = db.execute(
            f'SELECT * FROM "{table_name}"'
        ).df()

    profile = {
        "table": table_name,
        "rows": len(frame),
        "columns": len(frame.columns),
        "duplicate_rows": int(
            frame.duplicated().sum()
        ),
        "column_profiles": {}
    }

    for column in frame.columns:
        series = frame[column]

        details = {
            "dtype": str(series.dtype),
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique())
        }

        if pd.api.types.is_numeric_dtype(series):
            valid = series.dropna()

            if len(valid):
                details.update({
                    "minimum": float(valid.min()),
                    "maximum": float(valid.max()),
                    "mean": float(valid.mean()),
                    "median": float(valid.median()),
                    "total": float(valid.sum())
                })

        profile["column_profiles"][column] = details

    return json_safe(profile)


# --------------------------------------------------
# MCP Tool 5: Reload data
# --------------------------------------------------

@mcp.tool()
def reload_data() -> dict:
    """
    Reload all Excel workbooks after their contents
    have been updated on disk.
    """
    return reload_workbooks()


# --------------------------------------------------
# Start the MCP server
# --------------------------------------------------

import os

if __name__ == "__main__":
    reload_workbooks()

    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = int(os.environ.get("PORT", "8000"))

    mcp.run(transport="streamable-http")