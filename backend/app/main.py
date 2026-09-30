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

# The Claude connector URL is the full path below, including the secret
# segment -- keep it out of source control (it comes from the
# MCP_PATH_SECRET env var).
app.mount(f"/mcp/{config.MCP_PATH_SECRET}", mcp.streamable_http_app())


@app.get("/healthz")
def healthz():
    return {"ok": True}
