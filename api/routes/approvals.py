"""api/routes/approvals.py — GET /approvals, GET /approvals/{id}"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import ApprovalRequest
from api.middleware import require_auth

router = APIRouter()


@router.get("/approvals")
def list_approvals(
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _auth=Depends(require_auth),
):
    """List approval requests, optionally filtered by status."""
    q = db.query(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    if status:
        q = q.filter(ApprovalRequest.status == status)
    rows = q.limit(limit).all()
    return [
        {
            "id": r.id,
            "lead_name": r.lead_name,
            "company": r.company,
            "ai_score": r.ai_score,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "decision_by": r.decision_by,
        }
        for r in rows
    ]


@router.get("/approvals/{request_id}")
def get_approval(
    request_id: str,
    db: Session = Depends(get_db),
    _auth=Depends(require_auth),
):
    """Get full detail for one approval request."""
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": req.id,
        "lead_id": req.lead_id,
        "lead_name": req.lead_name,
        "company": req.company,
        "title": req.title,
        "email": req.email,
        "linkedin_url": req.linkedin_url,
        "ai_score": req.ai_score,
        "ai_rationale": req.ai_rationale,
        "source_system": req.source_system,
        "status": req.status,
        "decision_by": req.decision_by,
        "decision_at": req.decision_at.isoformat() if req.decision_at else None,
        "webhook_fired": req.webhook_fired,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "expires_at": req.expires_at.isoformat() if req.expires_at else None,
    }
