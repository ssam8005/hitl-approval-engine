"""
telegram/callback_handler.py — Processes inline button callbacks.

When a reviewer taps Approve or Reject:
    1. Validate callback_data format
    2. Auth check — only TELEGRAM_CHAT_ID user can approve
    3. Update ApprovalRequest status (idempotent — second tap is no-op)
    4. Write AuditLog entry
    5. Edit Telegram card (replace buttons with outcome)
    6. If approved → fire webhook
    7. Answer callback_query (clears Telegram loading spinner)

Edge cases:
    - Duplicate tap: second call is no-op, no state change
    - Expired request: inform reviewer, do not change state
    - Webhook failure: AuditLog entry + Telegram alert, no silent drop
"""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def handle_callback(callback: dict, cfg):
    """Process a Telegram inline keyboard callback_query."""
    from database.connection import _SessionLocal
    from database.models import ApprovalRequest, AuditLog
    from webhook.dispatcher import WebhookDispatcher
    from telegram.bot import edit_card, send_text, _tg_post

    data = callback.get("data", "")
    from_user = callback.get("from", {})
    actor = from_user.get("username") or str(from_user.get("id", "unknown"))
    chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))
    message_id = callback.get("message", {}).get("message_id")
    callback_id = callback.get("id")

    # Auth: only the configured chat owner can approve
    if chat_id != str(cfg.telegram_chat_id) and str(from_user.get("id")) != str(cfg.telegram_chat_id):
        _tg_post(cfg.telegram_bot_token, "answerCallbackQuery",
                 {"callback_query_id": callback_id, "text": "Unauthorized."})
        return

    if not data.startswith(("approve:", "reject:")):
        return

    action, request_id = data.split(":", 1)

    db = _SessionLocal()
    try:
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
        if not req:
            _tg_post(cfg.telegram_bot_token, "answerCallbackQuery",
                     {"callback_query_id": callback_id, "text": "Request not found."})
            return

        # Idempotent — already decided
        if req.status not in ("pending",):
            _tg_post(cfg.telegram_bot_token, "answerCallbackQuery",
                     {"callback_query_id": callback_id, "text": f"Already {req.status}."})
            return

        # Expired
        if req.expires_at and datetime.now(timezone.utc) > req.expires_at.replace(tzinfo=timezone.utc):
            _tg_post(cfg.telegram_bot_token, "answerCallbackQuery",
                     {"callback_query_id": callback_id, "text": "This request has expired."})
            return

        # Apply decision
        now = datetime.now(timezone.utc)
        req.status = action + "d"   # approved | rejected
        req.decision_by = actor
        req.decision_at = now

        db.add(AuditLog(
            request_id=request_id,
            event_type=req.status,
            actor=actor,
            detail=json.dumps({"action": action, "score": req.ai_score}),
            timestamp=now,
        ))
        db.commit()

        # Edit Telegram card
        outcome_emoji = "✅" if action == "approve" else "❌"
        new_text = (
            f"{outcome_emoji} *{action.upper()}D* by @{actor}\n"
            f"Lead: {req.lead_name} | Score: {req.ai_score:.0f}\n"
            f"Time: {now.strftime('%b %d %H:%M UTC')}\n"
            f"ID: `{request_id}`"
        )
        if req.telegram_message_id:
            edit_card(cfg.telegram_bot_token, cfg.telegram_chat_id, req.telegram_message_id, new_text)

        # Fire webhook on approval
        if action == "approve":
            dispatcher = WebhookDispatcher(cfg)
            success, code = dispatcher.dispatch(req)
            req.webhook_fired = success
            req.webhook_fired_at = now
            req.webhook_response_code = code
            db.add(AuditLog(
                request_id=request_id,
                event_type="webhook_fired" if success else "webhook_failed",
                actor="system",
                detail=json.dumps({"status_code": code, "success": success}),
                timestamp=now,
            ))
            db.commit()
            if not success:
                send_text(cfg.telegram_bot_token, cfg.telegram_chat_id,
                          f"⚠️ Webhook failed for {req.lead_name} ({request_id}). Manual follow-up needed.")

        _tg_post(cfg.telegram_bot_token, "answerCallbackQuery",
                 {"callback_query_id": callback_id, "text": f"Marked as {req.status}."})
    finally:
        db.close()
