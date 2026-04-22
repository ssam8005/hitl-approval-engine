"""
webhook/dispatcher.py — Fires downstream webhooks on approval decisions.

Retry policy: 3 attempts with exponential backoff (1s, 2s, 4s).
On all-attempt failure: logs to caller for AuditLog insertion + Telegram alert.
Never silently drops a failed webhook.
"""
import json
import logging
import time
import requests

logger = logging.getLogger(__name__)

RETRY_DELAYS = [1, 2, 4]


class WebhookDispatcher:
    """POST approval payload to downstream n8n / Zapier / custom webhook."""

    def __init__(self, cfg):
        self.url = cfg.n8n_webhook_url
        self.secret = cfg.n8n_webhook_secret
        self.timeout = cfg.webhook_timeout

    def _build_payload(self, req) -> dict:
        return {
            "event": "lead_approved",
            "request_id": req.id,
            "lead_id": req.lead_id,
            "lead_name": req.lead_name,
            "company": req.company,
            "title": req.title,
            "email": req.email,
            "linkedin_url": req.linkedin_url,
            "ai_score": req.ai_score,
            "approved_by": req.decision_by,
            "approved_at": req.decision_at.isoformat() if req.decision_at else None,
            "source_system": req.source_system,
        }

    def dispatch(self, req) -> tuple:
        """
        POST to downstream webhook with retry.

        Returns: (success: bool, http_status: int)
        """
        payload = self._build_payload(req)
        headers = {"Content-Type": "application/json"}
        if self.secret:
            headers["X-Webhook-Secret"] = self.secret

        last_status = 0
        for attempt, delay in enumerate(RETRY_DELAYS, 1):
            try:
                resp = requests.post(self.url, json=payload, headers=headers, timeout=self.timeout)
                if resp.status_code < 300:
                    logger.info(f"Webhook OK: {req.id} → {resp.status_code}")
                    return True, resp.status_code
                last_status = resp.status_code
                logger.warning(f"Webhook attempt {attempt} failed: {resp.status_code}")
            except requests.exceptions.RequestException as exc:
                logger.error(f"Webhook attempt {attempt} error: {exc}")
            if attempt < len(RETRY_DELAYS):
                time.sleep(delay)

        logger.error(f"Webhook failed after {len(RETRY_DELAYS)} attempts: {req.id}")
        return False, last_status
