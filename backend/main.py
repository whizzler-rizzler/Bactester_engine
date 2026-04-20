"""FastAPI application entrypoint.

Run locally:
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router

app = FastAPI(
    title="Bactester Engine API",
    version="0.1.0",
    description="Backtesting engine for crypto strategies on Binance 1m data.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"ok": True, "service": "bactester-engine", "docs": "/docs"}
