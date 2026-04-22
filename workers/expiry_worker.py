"""
workers/expiry_worker.py — Background thread that expires pending approvals.

Runs every 60 seconds. For each expired pending request:
    1. Update status to 'expired'
    2. Apply DEFAULT_APPROVAL_ACTION (approve | reject)
    3. If approve: fire downstream webhook
    4. Edit Telegram card to show expiry outcome
    5. Insert AuditLog entry (immutable)

Uses threading.Timer — no Celery/Redis dependency for single-process deployments.
For high-volume (>500 approvals/day), swap to Celery + PostgreSQL backend.
"""
import json
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _run_expiry(cfg):
    """Scan and expire overdue pending requests. Reschedules itself."""
    from database.connection import _SessionLocal
    from database.models import ApprovalRequest, AuditLog
    from webhook.dispatcher import WebhookDispatcher
    from telegram.bot import edit_card

    db = _SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        expired = db.query(ApprovalRequest).filter(
            ApprovalRequest.status == "pending",
            ApprovalRequest.expires_at < now,
        ).all()

        for req in expired:
            action = cfg.default_approval_action  # approve | reject
            req.status = "expired"
            req.decision_by = f"system:expiry:{action}"
            req.decision_at = now

            db.add(AuditLog(
                request_id=req.id,
                event_type="expired",
                actor="system",
                detail=json.dumps({"action": action, "expired_at": now.isoformat()}),
                timestamp=now,
            ))
            db.commit()

            if action == "approve":
                dispatcher = WebhookDispatcher(cfg)
                success, code = dispatcher.dispatch(req)
                req.webhook_fired = success
                req.webhook_fired_at = now
                req.webhook_response_code = code
                db.add(AuditLog(
                    request_id=req.id,
                    event_type="webhook_fired" if success else "webhook_failed",
                    actor="system",
                    detail=json.dumps({"status_code": code}),
                    timestamp=now,
                ))
                db.commit()

            # Edit Telegram card
            if req.telegram_message_id:
                outcome = "auto-approved (TTL expiry)" if action == "approve" else "expired — no action"
                try:
                    edit_card(
                        cfg.telegram_bot_token,
                        cfg.telegram_chat_id,
                        req.telegram_message_id,
                        f"⏰ *EXPIRED*\nLead: {req.lead_name}\nOutcome: {outcome}\nID: `{req.id}`",
                    )
                except Exception:
                    pass

            if expired:
                logger.info(f"Expired {len(expired)} pending approval(s)")

    except Exception as exc:
        logger.error(f"Expiry worker error: {exc}")
    finally:
        db.close()

    # Reschedule
    t = threading.Timer(60, _run_expiry, args=(cfg,))
    t.daemon = True
    t.start()


def start_expiry_worker(cfg=None):
    """Start the expiry worker. Called at FastAPI app startup."""
    if cfg is None:
        from config import get_settings
        cfg = get_settings()
    t = threading.Timer(60, _run_expiry, args=(cfg,))
    t.daemon = True
    t.start()
    logger.info("Expiry worker started (60s interval)")
