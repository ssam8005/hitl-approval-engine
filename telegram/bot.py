"""
telegram/bot.py — Telegram Bot API wrapper.

Supports polling (development) and webhook (production) modes.
Uses urllib.request for zero extra dependencies beyond requirements.txt.
"""
import json
import logging
import threading
import urllib.request
import urllib.parse
from telegram.card_formatter import format_card, build_keyboard
from telegram.callback_handler import handle_callback

logger = logging.getLogger(__name__)
_polling_thread = None


def _tg_post(bot_token: str, method: str, payload: dict) -> dict:
    """POST to Telegram Bot API. Returns parsed JSON response."""
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def send_approval_card(req, cfg) -> int:
    """Post approval card to Telegram. Returns message_id."""
    text = format_card(req)
    keyboard = build_keyboard(req.id)
    result = _tg_post(cfg.telegram_bot_token, "sendMessage", {
        "chat_id": cfg.telegram_chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": keyboard,
    })
    return result.get("result", {}).get("message_id")


def send_text(bot_token: str, chat_id: str, text: str):
    """Send a plain text message to Telegram."""
    try:
        _tg_post(bot_token, "sendMessage", {"chat_id": chat_id, "text": text})
    except Exception as exc:
        logger.error(f"Telegram send_text failed: {exc}")


def edit_card(bot_token: str, chat_id: str, message_id: int, new_text: str):
    """Edit an existing card message (replaces buttons with outcome text)."""
    try:
        _tg_post(bot_token, "editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text,
            "parse_mode": "Markdown",
        })
    except Exception as exc:
        logger.warning(f"Card edit failed: {exc}")


def _polling_loop(cfg):
    """Long-poll for Telegram updates. Runs in daemon thread."""
    offset = 0
    logger.info("Telegram polling started")
    while True:
        try:
            result = _tg_post(cfg.telegram_bot_token, "getUpdates", {
                "offset": offset, "timeout": 30, "allowed_updates": ["callback_query"]
            })
            for update in result.get("result", []):
                offset = update["update_id"] + 1
                cb = update.get("callback_query")
                if cb:
                    try:
                        handle_callback(cb, cfg)
                    except Exception as exc:
                        logger.error(f"Callback handling error: {exc}")
        except Exception as exc:
            logger.warning(f"Polling error: {exc}")
            import time; time.sleep(5)


def start_polling_thread(cfg=None):
    """Start background polling thread. Called at app startup."""
    global _polling_thread
    if _polling_thread and _polling_thread.is_alive():
        return
    if cfg is None:
        from config import get_settings
        cfg = get_settings()
    t = threading.Thread(target=_polling_loop, args=(cfg,), daemon=True, name="telegram-poll")
    t.start()
    _polling_thread = t
