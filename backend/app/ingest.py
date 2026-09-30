import io
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from . import cache, catalog, config
from .db import get_engine, storage_bucket
from .naming import make_table_name, unique_columns


def _read_sheets(file_name: str, content: bytes) -> dict[str, pd.DataFrame]:
    suffix = Path(file_name).suffix.lower()

    if suffix == ".csv":
        return {Path(file_name).stem: pd.read_csv(io.BytesIO(content))}

    if suffix in (".xlsx", ".xlsm"):
        return pd.read_excel(io.BytesIO(content), sheet_name=None, engine="openpyxl")

    raise ValueError(f"Unsupported file type: {suffix}")


def ingest_file(*, directory_path: str, file_name: str, content: bytes) -> dict:
    if len(content) > config.MAX_FILE_MB * 1024 * 1024:
        raise ValueError("File exceeds size limit")

    directory_path = directory_path.strip("/")
    sheets = _read_sheets(file_name, content)
    file_type = "csv" if file_name.lower().endswith(".csv") else "xlsx"

    storage_path = f"{directory_path}/{file_name}" if directory_path else file_name
    storage_bucket().upload(
        storage_path, content, {"upsert": "true"}
    )

    engine = get_engine()
    created = []
    skipped = []

    for sheet_name, frame in sheets.items():
        if frame.empty:
            skipped.append(sheet_name)
            continue

        frame.columns = unique_columns(frame.columns)
        table_name = make_table_name(directory_path, file_name, sheet_name)

        frame.to_sql(
            table_name,
            engine,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=1000,
        )

        column_schema = [
            {"column": column, "dtype": str(frame[column].dtype)}
            for column in frame.columns
        ]

        entry = catalog.upsert_catalog_entry(
            directory_path=directory_path,
            file_name=file_name,
            sheet_name=sheet_name,
            table_name=table_name,
            file_type=file_type,
            row_count=len(frame),
            column_schema=column_schema,
            storage_path=storage_path,
        )

        created.append(entry)

    cache.reload_cache()

    return {"created": created, "skipped_empty_sheets": skipped}


def delete_table(table_name: str) -> None:
    entry = catalog.get_catalog_entry(table_name)

    if entry is None:
        raise ValueError("Unknown table")

    deleted = catalog.delete_catalog_entry(table_name)

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f'drop table if exists "{table_name}"'))

    storage_path = deleted.get("storage_path") if deleted else None

    if storage_path:
        remaining = [
            row for row in catalog.list_catalog() if row["storage_path"] == storage_path
        ]

        if not remaining:
            try:
                storage_bucket().remove([storage_path])
            except Exception:
                pass

    cache.reload_cache()


def delete_file(directory_path: str, file_name: str) -> int:
    directory_path = directory_path.strip("/")
    entries = [
        row
        for row in catalog.list_catalog()
        if row["directory_path"] == directory_path and row["file_name"] == file_name
    ]

    for entry in entries:
        delete_table(entry["table_name"])

    return len(entries)


def delete_directory(directory_path: str) -> int:
    directory_path = directory_path.strip("/")
    entries = [
        row
        for row in catalog.list_catalog()
        if row["directory_path"] == directory_path
    ]

    for entry in entries:
        delete_table(entry["table_name"])

    return len(entries)
