#!/usr/bin/env python3
"""
HITL Approval Engine — FastAPI Application
==========================================
Sits between any AI decision engine and downstream outreach actions.
Human-in-the-loop governance via Telegram inline keyboard approvals.

Architecture:
    AI scores lead → POST /submit → threshold routing →
    Telegram card (review zone) → human approves/rejects →
    webhook fires to n8n → outreach sequence begins.

Usage:
    pip install -r requirements.txt
    cp .env.example .env  && nano .env
    uvicorn main:app --host 0.0.0.0 --port 8080

API docs: http://localhost:8080/docs

Part of the Neural-GTM Sprint governance stack.
© myAutoBots.AI — Sammy Samet | myautobots.ai
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from database.connection import init_db
from api.routes import submissions, approvals, health
from telegram.bot import start_polling_thread
from workers.expiry_worker import start_expiry_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, start Telegram polling, start expiry worker."""
    init_db()
    from config import get_settings
    cfg = get_settings()
    if cfg.telegram_mode == "polling":
        start_polling_thread(cfg)
    start_expiry_worker(cfg)
    yield
    # Graceful shutdown: daemon threads die with process


app = FastAPI(
    title="HITL Approval Engine",
    description=(
        "Human-in-the-loop governance for AI-scored outreach pipelines. "
        "Telegram-native approval cards with Approve/Reject inline buttons. "
        "Part of the Neural-GTM Sprint — myAutoBots.AI."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(submissions.router, tags=["Submissions"])
app.include_router(approvals.router, tags=["Approvals"])
app.include_router(health.router, tags=["Health"])
