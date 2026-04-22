"""
scoring/threshold_router.py — Routes AI decisions based on score thresholds.

Three zones:
    auto_approved  (score >= AUTO_APPROVE_SCORE_THRESHOLD, default 85)
        High-confidence ICP. Fires webhook immediately. FYI Telegram only.

    pending_review (AUTO_REJECT_THRESHOLD < score < AUTO_APPROVE_THRESHOLD)
        Ambiguous leads. Posts Telegram card + waits for human decision.
        Target: ~30-50% of volume in a well-tuned pipeline.

    auto_rejected  (score <= AUTO_REJECT_THRESHOLD, default 30)
        Discarded. Logged to AuditLog. No Telegram noise.

Tune thresholds via .env after 30 days of live data to match your
actual approve/reject distribution.
"""


def route(score: float, cfg) -> str:
    """
    Return routing decision string for a given AI score.

    Returns: 'auto_approved' | 'pending_review' | 'auto_rejected'
    """
    if score >= cfg.auto_approve_threshold:
        return "auto_approved"
    if score <= cfg.auto_reject_threshold:
        return "auto_rejected"
    return "pending_review"
