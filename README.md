# Neerus MCP — Excel/CSV analytics for Claude

Upload spreadsheets through a web UI, they land as tables in Supabase, and
Claude queries them through an MCP connector.

```
frontend/  React + Vite admin UI          -> deployed to Vercel
backend/   FastAPI + MCP server           -> deployed to Render
supabase/  SQL migration (catalog table)  -> run once in Supabase
```

## 1. Create the Supabase project

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor**, paste the contents of
   [`supabase/migrations/0001_init.sql`](supabase/migrations/0001_init.sql), and run it.
   This creates the `dataset_catalog` table and a private `raw-uploads` storage bucket.
3. Collect three values from **Project Settings**:
   - **Database -> Connection string -> URI** -> `DATABASE_URL` (change the
     `postgresql://` prefix to `postgresql+psycopg2://` -- see the comment in
     `backend/.env.example` for why)
   - **API Keys -> Project URL** -> `SUPABASE_URL`
   - **API Keys -> Secret keys** (`sb_secret_...`) -> `SUPABASE_SECRET_KEY` (never expose this to the browser)

## 2. Backend (Render)

```
cd backend
cp .env.example .env      # fill in the values below for local testing
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Generate the two secrets it needs:
```
python -c "import secrets; print(secrets.token_urlsafe(32))"   # MCP_PATH_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"   # SESSION_SECRET
```

Required environment variables (see `backend/.env.example` for the full list
with comments): `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`,
`MCP_PATH_SECRET`, `ADMIN_PASSWORD`, `SESSION_SECRET`, `CORS_ORIGINS`.

**Deploy:** push this repo to GitHub, then in Render choose **New -> Blueprint**
and point it at the repo — it will read [`render.yaml`](render.yaml) and create
the service. Render will prompt you to fill in the secret env vars (marked
`sync: false` in the blueprint) since they aren't stored in the file. Note
its assigned URL, e.g. `https://neerus-mcp-backend.onrender.com`.

The `starter` plan in `render.yaml` avoids cold starts; switch it to `free` if
occasional slow first-responses are fine.

### Migrate the existing local data (optional)

The repo's `data/retail_mock_financial_data.xlsx` isn't uploaded anywhere yet.
To push it into Supabase once the backend's env vars are set locally:
```
cd backend
python -m scripts.migrate_local_data
```

## 3. Frontend (Vercel)

```
cd frontend
cp .env.example .env.local   # set VITE_API_URL to your Render backend URL
npm install
npm run dev
```

**Deploy:** import the repo into [Vercel](https://vercel.com), set the project
root to `frontend/`, and add `VITE_API_URL` (your Render backend URL, no
trailing slash) as an environment variable. Vercel auto-detects the Vite
build.

Once both are deployed, add the frontend's Vercel URL to the backend's
`CORS_ORIGINS` env var on Render (comma-separated if there's more than one),
and redeploy the backend.

## 4. Connect Claude Desktop

Claude Desktop -> Settings -> Connectors -> **Add custom connector**, and
enter:
```
https://<your-render-backend>/mcp/<MCP_PATH_SECRET>
```
using the exact `MCP_PATH_SECRET` value you set on the backend. This URL has
no separate login step — the random secret in the path *is* the credential,
so treat it like a password (Claude's simple "static header" auth option is
currently in a limited beta most accounts can't use yet; see the note below).
Claude should list 5 tools: `list_datasets`, `get_schema`, `execute_query`,
`get_data_profile`, `reload_data`.

## 5. Using the admin UI

Open the Vercel URL, sign in with `ADMIN_PASSWORD`, pick or create a directory
in the sidebar, and drag `.xlsx`/`.csv` files onto it. Every sheet becomes its
own Postgres table; re-uploading the same file/sheet replaces its table.
Deleting a table or folder removes it from Postgres and Storage immediately.
Claude's cached view of the data refreshes automatically after every
upload/delete — call the `reload_data` tool manually only if you changed data
outside the UI.

## Security notes

- The MCP endpoint's only protection is the unguessable path secret. If you
  ever suspect it's leaked, generate a new `MCP_PATH_SECRET`, redeploy, and
  re-add the connector in Claude with the new URL.
- `execute_query` only allows single, read-only `SELECT` statements against
  tables that exist in the catalog (enforced by `backend/app/sql_guard.py`
  parsing the SQL with `sqlglot`, not by string filtering).
- The admin UI's session cookie is separate from the MCP secret and is
  required for every upload/delete/list call.
