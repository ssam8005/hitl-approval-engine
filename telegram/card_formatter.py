"""
telegram/card_formatter.py — Builds the Telegram approval card message.

Card design: everything a reviewer needs to decide in < 10 seconds.
One message, no external lookups, score badge for instant severity read.
"""

SCORE_BADGES = [
    (85, 100, "🟢 HIGH PRIORITY"),
    (65,  84, "🟡 QUALIFIED"),
    (45,  64, "🟠 BORDERLINE"),
    ( 0,  44, "🔴 WEAK FIT"),
]


def get_badge(score: float) -> str:
    for lo, hi, label in SCORE_BADGES:
        if lo <= score <= hi:
            return label
    return "⚪ UNSCORED"


def format_card(req) -> str:
    """Build the card text (Telegram MarkdownV2 compatible)."""
    badge = get_badge(req.ai_score)
    rationale = (req.ai_rationale or "No rationale provided")
    if len(rationale) > 280:
        rationale = rationale[:277] + "..."

    linkedin = f"🔗 {req.linkedin_url}" if req.linkedin_url else "🔗 LinkedIn: not on file"
    expiry = req.expires_at.strftime("%b %d %H:%M UTC") if req.expires_at else "unknown"

    return (
        f"*{badge}* — Score: {req.ai_score:.0f}/100\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *{req.lead_name}*\n"
        f"🏢 {req.company or 'Unknown company'}\n"
        f"💼 {req.title or 'Unknown title'}\n"
        f"📧 {req.email or 'No email on file'}\n"
        f"{linkedin}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 *AI Rationale:*\n{rationale}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Source: `{req.source_system}`\n"
        f"⏱ Expires: {expiry}\n"
        f"🆔 `{req.id}`"
    )


def build_keyboard(request_id: str) -> dict:
    """Telegram inline keyboard with Approve / Reject buttons."""
    return {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve:{request_id}"},
            {"text": "❌ Reject",  "callback_data": f"reject:{request_id}"},
        ]]
    }
