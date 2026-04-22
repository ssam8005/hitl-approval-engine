"""
api/routes/submissions.py — POST /submit

Receives an AI-scored lead decision from any upstream system (n8n workflow,
LangGraph agent, agentic-lead-scorer, etc.) and routes it for human review
or auto-decision based on score thresholds.

Returns 202 Accepted immediately. Telegram notification and webhook dispatch
happen asynchronously — callers should not wait for downstream actions.
"""
import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import ApprovalRequest, AuditLog
from api.middleware import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


class LeadSubmission(BaseModel):
    lead_id: str
    lead_name: str
    company: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    ai_score: float = Field(..., ge=0.0, le=100.0)
    ai_rationale: Optional[str] = None
    source_system: str = "unknown"


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
def submit_lead(
    payload: LeadSubmission,
    db: Session = Depends(get_db),
    _auth=Depends(require_auth),
):
    """
    Accept an AI-scored lead for HITL review.

    Routing logic (via scoring/threshold_router.py):
        score >= AUTO_APPROVE_THRESHOLD  → auto-approve, webhook fires immediately
        score <= AUTO_REJECT_THRESHOLD   → auto-reject, no webhook
        score in between                 → Telegram approval card posted

    Returns: {request_id, routing: pending_review | auto_approved | auto_rejected}
    """
    from config import get_settings
    from scoring.threshold_router import route
    from telegram.bot import send_approval_card
    from webhook.dispatcher import WebhookDispatcher

    cfg = get_settings()
    request_id = str(uuid.uuid4())[:8]
    expires_at = datetime.now(timezone.utc) + timedelta(hours=cfg.approval_ttl_hours)

    req = ApprovalRequest(
        id=request_id,
        lead_id=payload.lead_id,
        lead_name=payload.lead_name,
        company=payload.company,
        title=payload.title,
        email=payload.email,
        linkedin_url=payload.linkedin_url,
        ai_score=payload.ai_score,
        ai_rationale=payload.ai_rationale,
        source_system=payload.source_system,
        status="pending",
        created_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )
    db.add(req)

    audit = AuditLog(
        request_id=request_id,
        event_type="submitted",
        actor=payload.source_system,
        detail=json.dumps({"score": payload.ai_score, "lead": payload.lead_name}),
        timestamp=datetime.now(timezone.utc),
    )
    db.add(audit)
    db.commit()

    routing = route(payload.ai_score, cfg)

    if routing == "auto_approved":
        req.status = "auto_approved"
        req.decision_by = "system"
        req.decision_at = datetime.now(timezone.utc)
        db.add(AuditLog(request_id=request_id, event_type="auto_approved",
                        actor="system:auto_approve",
                        detail=json.dumps({"score": payload.ai_score, "threshold": cfg.auto_approve_threshold})))
        db.commit()
        dispatcher = WebhookDispatcher(cfg)
        dispatcher.dispatch(req)

    elif routing == "auto_rejected":
        req.status = "auto_rejected"
        req.decision_by = "system"
        req.decision_at = datetime.now(timezone.utc)
        db.add(AuditLog(request_id=request_id, event_type="auto_rejected",
                        actor="system:auto_reject",
                        detail=json.dumps({"score": payload.ai_score, "threshold": cfg.auto_reject_threshold})))
        db.commit()

    else:
        # Send Telegram card for human review
        try:
            msg_id = send_approval_card(req, cfg)
            if msg_id:
                req.telegram_message_id = msg_id
                db.add(AuditLog(request_id=request_id, event_type="card_sent",
                                actor="system", detail=json.dumps({"message_id": msg_id})))
                db.commit()
        except Exception as exc:
            logger.error(f"Telegram card failed for {request_id}: {exc}")

    return {"request_id": request_id, "routing": routing}
