from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from supabase import create_client, Client

from . import config


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """SQLAlchemy engine for direct Postgres access (DDL, bulk load, catalog)."""
    return create_engine(config.DATABASE_URL, pool_pre_ping=True, pool_size=5)


@lru_cache(maxsize=1)
def get_storage_client() -> Client:
    """Supabase client, used only for Storage (the original uploaded files)."""
    return create_client(config.SUPABASE_URL, config.SUPABASE_SECRET_KEY)


def storage_bucket():
    return get_storage_client().storage.from_(config.SUPABASE_STORAGE_BUCKET)
