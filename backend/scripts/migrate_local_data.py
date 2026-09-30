"""
One-off: push the .xlsx files already sitting in the repo's local `data/`
folder into Supabase, using the same ingestion path the upload API uses.

Run from the `backend/` directory after DATABASE_URL / SUPABASE_* env vars
are set (or a .env file is present):

    python -m scripts.migrate_local_data
"""

from pathlib import Path

from app import ingest

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def main() -> None:
    files = sorted(DATA_DIR.glob("*.xlsx"))

    if not files:
        print(f"No .xlsx files found in {DATA_DIR}")
        return

    for file in files:
        print(f"Uploading {file.name} ...")
        result = ingest.ingest_file(
            directory_path="",
            file_name=file.name,
            content=file.read_bytes(),
        )
        print(f"  created {len(result['created'])} table(s)")


if __name__ == "__main__":
    main()
