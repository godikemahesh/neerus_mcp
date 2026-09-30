import json

from sqlalchemy import text

from .db import get_engine


def list_catalog() -> list[dict]:
    with get_engine().begin() as conn:
        rows = conn.execute(
            text(
                """
                select id, directory_path, file_name, sheet_name, table_name,
                       file_type, row_count, column_schema, storage_path,
                       uploaded_at, updated_at
                from dataset_catalog
                order by directory_path, file_name, sheet_name
                """
            )
        ).mappings()

        return [dict(row) for row in rows]


def get_catalog_entry(table_name: str) -> dict | None:
    with get_engine().begin() as conn:
        row = conn.execute(
            text("select * from dataset_catalog where table_name = :table_name"),
            {"table_name": table_name},
        ).mappings().first()

        return dict(row) if row else None


def find_existing_table_name(
    directory_path: str, file_name: str, sheet_name: str
) -> str | None:
    with get_engine().begin() as conn:
        row = conn.execute(
            text(
                """
                select table_name from dataset_catalog
                where directory_path = :directory_path
                  and file_name = :file_name
                  and sheet_name = :sheet_name
                """
            ),
            {
                "directory_path": directory_path,
                "file_name": file_name,
                "sheet_name": sheet_name,
            },
        ).first()

        return row[0] if row else None


def upsert_catalog_entry(
    *,
    directory_path: str,
    file_name: str,
    sheet_name: str,
    table_name: str,
    file_type: str,
    row_count: int,
    column_schema: list[dict],
    storage_path: str | None,
) -> dict:
    with get_engine().begin() as conn:
        row = conn.execute(
            text(
                """
                insert into dataset_catalog (
                    directory_path, file_name, sheet_name, table_name,
                    file_type, row_count, column_schema, storage_path
                )
                values (
                    :directory_path, :file_name, :sheet_name, :table_name,
                    :file_type, :row_count, cast(:column_schema as jsonb), :storage_path
                )
                on conflict (directory_path, file_name, sheet_name)
                do update set
                    table_name = excluded.table_name,
                    file_type = excluded.file_type,
                    row_count = excluded.row_count,
                    column_schema = excluded.column_schema,
                    storage_path = excluded.storage_path,
                    updated_at = now()
                returning id, directory_path, file_name, sheet_name, table_name,
                          file_type, row_count, column_schema, storage_path,
                          uploaded_at, updated_at
                """
            ),
            {
                "directory_path": directory_path,
                "file_name": file_name,
                "sheet_name": sheet_name,
                "table_name": table_name,
                "file_type": file_type,
                "row_count": row_count,
                "column_schema": json.dumps(column_schema),
                "storage_path": storage_path,
            },
        ).mappings().first()

        return dict(row)


def delete_catalog_entry(table_name: str) -> dict | None:
    with get_engine().begin() as conn:
        row = conn.execute(
            text(
                "delete from dataset_catalog where table_name = :table_name "
                "returning storage_path"
            ),
            {"table_name": table_name},
        ).first()

        return dict(row._mapping) if row else None
