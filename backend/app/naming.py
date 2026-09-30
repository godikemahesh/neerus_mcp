import hashlib
import re

import numpy as np
import pandas as pd


def clean_name(name) -> str:
    """Convert an arbitrary sheet/column name to a SQL identifier."""
    name = re.sub(r"[^a-zA-Z0-9_]+", "_", str(name)).strip("_").lower()

    if not name:
        name = "sheet"

    if name[0].isdigit():
        name = "t_" + name

    return name


def unique_columns(columns) -> list[str]:
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


def make_table_name(directory_path: str, file_name: str, sheet_name: str) -> str:
    """
    A deterministic, unique-enough Postgres table name for a given
    (directory, file, sheet) triple. Deterministic so re-uploading the same
    sheet replaces the same physical table instead of creating a new one.
    """
    key = f"{directory_path}\0{file_name}\0{sheet_name}".lower()
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]

    slug = clean_name(f"{file_name}_{sheet_name}")[:40].strip("_") or "sheet"

    return f"ds_{slug}_{digest}"


def json_safe(value):
    """Convert NumPy and Pandas values to JSON-serializable values."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}

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
