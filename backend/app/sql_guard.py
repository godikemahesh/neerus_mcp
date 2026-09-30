import sqlglot
from sqlglot import exp

from . import config

FORBIDDEN_STATEMENTS = (
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

BLOCKED_FUNCTIONS = {
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


def validate_sql(query: str, allowed_tables: set[str]) -> str:
    """
    Permit one read-only analytical SQL statement against the given set of
    allowed table names. Raises ValueError on anything else.
    """
    if len(query) > config.MAX_QUERY_LENGTH:
        raise ValueError("SQL query is too long")

    statements = sqlglot.parse(query, read="duckdb")

    if len(statements) != 1:
        raise ValueError("Exactly one SQL statement is allowed")

    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise ValueError("Only read-only SELECT queries are allowed")

    if any(isinstance(node, FORBIDDEN_STATEMENTS) for node in tree.walk()):
        raise ValueError("Unsafe SQL operation")

    # Do not permit arbitrary table-valued functions.
    for node in tree.find_all(exp.Table):
        if not isinstance(node.this, exp.Identifier):
            raise ValueError("Table functions are not permitted")

    # CTE names are permitted as local query tables.
    cte_names = {cte.alias.lower() for cte in tree.find_all(exp.CTE)}
    allowed = set(allowed_tables) | cte_names

    for table in tree.find_all(exp.Table):
        name = table.name.lower()

        if name not in allowed:
            raise ValueError(f"Table is not permitted: {name}")

        if table.db or table.catalog:
            raise ValueError("Qualified external tables are not allowed")

    for function in tree.find_all(exp.Func):
        name = function.sql_name().lower()

        if name in BLOCKED_FUNCTIONS:
            raise ValueError(f"Function is not permitted: {name}")

    return tree.sql(dialect="duckdb")
