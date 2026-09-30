import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def _split_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


# Direct Postgres connection to the Supabase project (Settings -> Database ->
# Connection string -> URI, using the "Session pooler" or direct connection).
DATABASE_URL = _require("DATABASE_URL")

# Project Settings -> API Keys -> Secret keys. This bypasses Row Level
# Security, so it must never be sent to the frontend. (Supabase's newer
# "secret key", format sb_secret_..., replaces the legacy service_role JWT --
# it's a drop-in value for create_client, no code changes needed either way.)
SUPABASE_URL = _require("SUPABASE_URL")
SUPABASE_SECRET_KEY = _require("SUPABASE_SECRET_KEY")
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "raw-uploads")

# Random, unguessable path segment. The Claude connector URL becomes
# https://<host>/mcp/<MCP_PATH_SECRET>/ -- generate with:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
MCP_PATH_SECRET = _require("MCP_PATH_SECRET")

# Shared login for the admin upload/delete UI.
ADMIN_PASSWORD = _require("ADMIN_PASSWORD")
SESSION_SECRET = _require("SESSION_SECRET")
SESSION_COOKIE_NAME = "neerus_admin_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 12  # 12 hours

# Set COOKIE_SECURE=false only for local http:// testing. Real deployments
# (Render + Vercel) are both https:// and must keep this true.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"

CORS_ORIGINS = _split_origins(os.environ.get("CORS_ORIGINS", ""))

MAX_ROWS = int(os.environ.get("MAX_ROWS", "200"))
MAX_FILE_MB = int(os.environ.get("MAX_FILE_MB", "30"))
MAX_QUERY_LENGTH = int(os.environ.get("MAX_QUERY_LENGTH", "10000"))
