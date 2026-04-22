"""
database/models.py — SQLAlchemy ORM models.

Two tables:
    approval_requests — one row per inbound AI decision, mutable lifecycle state
    audit_log         — immutable append-only record of every state transition

AuditLog is NEVER updated — only inserted. This satisfies HIPAA audit trail
requirements (45 CFR 164.312) and SOX control documentation needs.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, ForeignKey
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ApprovalRequest(Base):
    """
    One row per lead submitted for HITL review.

    Lifecycle: pending → approved | rejected | expired | auto_approved | auto_rejected
    """
    __tablename__ = "approval_requests"

    id = Column(String, primary_key=True)           # UUID4
    lead_id = Column(String, nullable=False, index=True)
    lead_name = Column(String, nullable=False)
    company = Column(String)
    title = Column(String)
    email = Column(String)
    linkedin_url = Column(String)

    ai_score = Column(Float, nullable=False)         # 0.0 – 100.0
    ai_rationale = Column(Text)
    source_system = Column(String, default="unknown")

    status = Column(String, default="pending")       # pending|approved|rejected|expired|auto_approved|auto_rejected
    decision_by = Column(String)                     # telegram username or "system"
    decision_at = Column(DateTime)
    decision_note = Column(Text)

    telegram_message_id = Column(Integer)            # for editing card on decision
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    webhook_fired = Column(Boolean, default=False)
    webhook_fired_at = Column(DateTime)
    webhook_response_code = Column(Integer)


class AuditLog(Base):
    """
    Immutable audit trail — every state change logged here.

    Design rule: only INSERT, never UPDATE or DELETE.
    Retention: configurable via AUDIT_RETENTION_DAYS (default 90 days).
    Compliance: HIPAA 45 CFR 164.312(b), SOX IT General Controls.
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, ForeignKey("approval_requests.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)      # submitted|card_sent|approved|rejected|webhook_fired|expired|auto_approved|auto_rejected
    actor = Column(String)                           # telegram username, "system", or API key fingerprint
    detail = Column(Text)                            # JSON blob with context
    timestamp = Column(DateTime, default=datetime.utcnow)
