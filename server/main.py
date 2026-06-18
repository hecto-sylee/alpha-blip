"""FastAPI app: REST API + static SPA shell. (00/01 implementation plan)"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import seed
from .api import (
    auth,
    clips,
    demo,
    matches,
    nearby,
    pets,
    privacy,
    quests,
    reactions,
    records,
    rooms,
    walks,
)
from .database import init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
INDEX_HTML = os.path.join(STATIC_DIR, "index.html")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed.run()
    yield


app = FastAPI(title="blip MVP", lifespan=lifespan)


# Uniform error envelope: { "error": { "code", "message" } }
@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.detail}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": {"code": 400, "message": exc.errors()}},
    )


# API routers (prefix /api)
for r in (auth, pets, walks, nearby, matches, records, clips, quests, rooms, reactions, privacy, demo):
    app.include_router(r.router, prefix="/api")

# Static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/healthz")
def healthz():
    return {"ok": True}


# SPA shell + client-side routing fallback.
@app.get("/")
def index():
    return FileResponse(INDEX_HTML)


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    # API/static routes are handled above; unknown GET paths fall back to SPA.
    if full_path.startswith("api/") or full_path.startswith("static/"):
        return JSONResponse(status_code=404, content={"error": {"code": 404, "message": "not found"}})
    return FileResponse(INDEX_HTML)
