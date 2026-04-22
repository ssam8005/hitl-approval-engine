"""api/routes/health.py — GET /health"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import ApprovalRequest

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Service health + live metrics. No auth required for uptime monitoring."""
    pending = db.query(ApprovalRequest).filter(ApprovalRequest.status == "pending").count()
    approved = db.query(ApprovalRequest).filter(ApprovalRequest.status == "approved").count()
    auto_approved = db.query(ApprovalRequest).filter(ApprovalRequest.status == "auto_approved").count()
    rejected = db.query(ApprovalRequest).filter(ApprovalRequest.status == "rejected").count()
    total_webhooks = db.query(ApprovalRequest).filter(ApprovalRequest.webhook_fired == True).count()
    return {
        "status": "ok",
        "pending_approvals": pending,
        "approved": approved,
        "auto_approved": auto_approved,
        "rejected": rejected,
        "webhooks_fired": total_webhooks,
    }
