# Telegram Bot Setup

Quick guide to get your Telegram bot running in < 5 minutes.

## Step 1: Create your bot

1. Open Telegram → search `@BotFather`
2. Send `/newbot`
3. Choose a name (e.g. "HITL Approvals") and a username (e.g. `my_hitl_bot`)
4. BotFather returns your **bot token** — copy it to `TELEGRAM_BOT_TOKEN` in `.env`

## Step 2: Get your Chat ID

1. Send any message to your new bot
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat":{"id":XXXXXXXXXX}` — that number is your `TELEGRAM_CHAT_ID`
4. Set it in `.env`

## Step 3: Start the engine

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Step 4: Test with sample payload

```bash
curl -X POST http://localhost:8080/submit \
  -H "X-API-Key: your_api_secret_key" \
  -H "Content-Type: application/json" \
  -d @sample_payloads/submit_lead.json
```

You should receive an approval card in Telegram within 2 seconds with ✅ Approve and ❌ Reject buttons.

## Production: Webhook Mode (optional)

For production with a public URL, switch from polling to webhook mode:

```env
TELEGRAM_MODE=webhook
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/telegram-webhook
```

Then register the webhook:
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://yourdomain.com/telegram-webhook"
```
