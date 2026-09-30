from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import cache, config
from .api import router as api_router
from .mcp_server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.reload_cache()

    async with mcp.session_manager.run():
        yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/healthz")
def healthz():
    return {"ok": True}


# Mounted at the root, not at "/mcp/<secret>": the sub-app's own route path
# (set in mcp_server.py) already *is* the full "/mcp/<secret>" path. Mounting
# it under an extra prefix here would make the sub-app's route pattern be
# "<prefix>/" internally, and a request to the connector URL *without* a
# trailing slash would get a 307 redirect to add one -- which is exactly
# what broke Claude Desktop's "Add custom connector" check (it doesn't
# follow that redirect). Every route above this line is matched first, so
# this catch-all can't shadow /api/* or /healthz.
app.mount("/", mcp.streamable_http_app())
