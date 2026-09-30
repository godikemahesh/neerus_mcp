from urllib.parse import urlparse

import pandas as pd
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from . import cache, config
from .config import MAX_ROWS
from .naming import json_safe
from .sql_guard import validate_sql

_public_host = urlparse(config.PUBLIC_BACKEND_URL).hostname

# The route path is the *entire* connector URL path (not just a mount
# prefix) so that hitting it without a trailing slash matches directly --
# see main.py for why this is mounted at the app root.
#
# transport_security must list the real public hostname: FastMCP's DNS
# rebinding protection otherwise only allows Host headers like localhost/
# 127.0.0.1 by default, and rejects every real request with 421.
mcp = FastMCP(
    "Neerus Excel Analytics",
    streamable_http_path=f"/mcp/{config.MCP_PATH_SECRET}",
    transport_security=TransportSecuritySettings(
        allowed_hosts=[_public_host, "127.0.0.1:*", "localhost:*", "[::1]:*"],
        allowed_origins=[config.PUBLIC_BACKEND_URL, "http://127.0.0.1:*", "http://localhost:*"],
    ),
)


@mcp.tool()
def list_datasets() -> dict:
    """
    List available spreadsheet tables, grouped by directory and then by the
    original file -- a multi-sheet Excel file appears once with all of its
    sheets nested under it, each with the table_name to use in execute_query
    or get_schema.

    Call this first when discovering the user's data.
    """
    _, datasets = cache.get_state()

    directories: dict[str, dict[str, list[dict]]] = {}

    for table_name, info in datasets.items():
        directory_bucket = directories.setdefault(info["directory"], {})
        file_bucket = directory_bucket.setdefault(info["file"], [])

        file_bucket.append(
            {
                "sheet": info["sheet"],
                "table_name": table_name,
                "rows": info["rows"],
                "columns": info["columns"],
            }
        )

    return {"directories": directories}


@mcp.tool()
def get_schema(table_name: str = "") -> dict:
    """
    Get SQL table schemas and example rows.

    Leave table_name empty to inspect every table.
    """
    db, datasets = cache.get_state()

    if table_name:
        if table_name not in datasets:
            return {"error": "Unknown table"}

        names = [table_name]
    else:
        names = list(datasets)

    result = {}

    for name in names:
        columns = db.execute(f'DESCRIBE SELECT * FROM "{name}"').fetchall()
        sample = db.execute(f'SELECT * FROM "{name}" LIMIT 3').df()

        result[name] = {
            "source": datasets[name],
            "schema": [{"column": row[0], "type": row[1]} for row in columns],
            "sample": json_safe(sample.to_dict(orient="records")),
        }

    return result


@mcp.tool()
def execute_query(sql: str) -> dict:
    """
    Run a read-only SQL query on the loaded spreadsheet data.

    Discover table names with list_datasets and column names with
    get_schema first.

    Supports filtering, grouping, joins, aggregations, window functions and
    date calculations.
    """
    try:
        db, datasets = cache.get_state()
        safe_sql = validate_sql(sql, allowed_tables=set(datasets))

        limited_sql = (
            "SELECT * FROM (" + safe_sql + f") AS result LIMIT {MAX_ROWS}"
        )

        result = db.execute(limited_sql).df()

        return {
            "columns": list(result.columns),
            "row_count": len(result),
            "rows": json_safe(result.to_dict(orient="records")),
            "limit": MAX_ROWS,
        }

    except Exception as error:
        return {"error": str(error)}


@mcp.tool()
def get_data_profile(table_name: str) -> dict:
    """
    Analyze column types, missing values and descriptive statistics for a
    table.
    """
    db, datasets = cache.get_state()

    if table_name not in datasets:
        return {"error": "Unknown table"}

    frame = db.execute(f'SELECT * FROM "{table_name}"').df()

    profile = {
        "table": table_name,
        "rows": len(frame),
        "columns": len(frame.columns),
        "duplicate_rows": int(frame.duplicated().sum()),
        "column_profiles": {},
    }

    for column in frame.columns:
        series = frame[column]

        details = {
            "dtype": str(series.dtype),
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique()),
        }

        if pd.api.types.is_numeric_dtype(series):
            valid = series.dropna()

            if len(valid):
                details.update(
                    {
                        "minimum": float(valid.min()),
                        "maximum": float(valid.max()),
                        "mean": float(valid.mean()),
                        "median": float(valid.median()),
                        "total": float(valid.sum()),
                    }
                )

        profile["column_profiles"][column] = details

    return json_safe(profile)


@mcp.tool()
def reload_data() -> dict:
    """
    Refresh the query cache after sheets have been uploaded, replaced or
    deleted through the admin UI.
    """
    return cache.reload_cache()
