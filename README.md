# HITL Approval Engine
### Human-in-the-Loop Governance for AI-Scored Outreach Pipelines

> "Every AI system that touches a human should have a human in the loop.
> This one does — with a full audit trail, Telegram delivery, and n8n integration."

![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=flat-square&logo=telegram)
![SQLite](https://img.shields.io/badge/SQLite-WAL%20mode-003B57?style=flat-square&logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## The Problem

Most "AI automation" for outreach fires directly to prospects with zero human check. Fine when AI accuracy is 95%. Catastrophic when it's 70%. One wrong message to a $500K prospect — wrong name, wrong company, wrong offer — costs more than the entire automation budget for the quarter.

This engine is the circuit breaker between AI decisions and human consequences.

---

## How It Works

```
Your AI scores a lead → POST /submit
        │
        ├── Score ≥ 85 → Auto-approve, webhook fires immediately
        ├── Score ≤ 30 → Auto-reject, discarded + logged
        └── Middle zone → Telegram card with ✅/❌ buttons
                              │
                          Human taps ✅
                              │
                          n8n webhook fires → outreach begins
```

---

## Quick Start (3 minutes)

```bash
git clone https://github.com/ssam8005/hitl-approval-engine
cd hitl-approval-engine
pip install -r requirements.txt
cp .env.example .env
# Configure: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, N8N_WEBHOOK_URL, API_SECRET_KEY

uvicorn main:app --host 0.0.0.0 --port 8080
```

**Test immediately with sample payload:**
```bash
curl -X POST http://localhost:8080/submit \
  -H "X-API-Key: your_api_secret_key" \
  -H "Content-Type: application/json" \
  -d @sample_payloads/submit_lead.json
```

→ Approval card appears in Telegram in ~2 seconds.

**API docs:** `http://localhost:8080/docs` (Swagger UI auto-generated)

---

## The Approval Card

What the reviewer sees in Telegram — everything needed to decide in < 10 seconds:

```
🟡 QUALIFIED — Score: 73/100
━━━━━━━━━━━━━━━━━━━━
👤 Jordan Blake
🏢 Acme SaaS
💼 VP of Sales
📧 jordan.blake@acmesaas.com
🔗 linkedin.com/in/jordanblake
━━━━━━━━━━━━━━━━━━━━
🤖 AI Rationale:
Strong ICP fit. Decision-maker title confirmed.
Visited pricing page 3x in 7 days. Series B
recently raised — active GTM investment signal.
━━━━━━━━━━━━━━━━━━━━
📡 Source: n8n-lead-scorer-v2
⏱ Expires: Apr 22 14:32 UTC
🆔 a3f1b2c4

[✅ Approve]  [❌ Reject]
```

On approval: buttons disappear, confirmed message shown, n8n webhook fires within seconds.

---

## Threshold Routing

| Zone | Score Range | Action | Human Review? |
|---|---|---|---|
| Auto-Approve | ≥ 85 | Webhook fires immediately | No (FYI Telegram only) |
| Review | 31–84 | Telegram card + buttons posted | Yes |
| Auto-Reject | ≤ 30 | Logged silently, discarded | No |

Configure via `.env`. After 30 days of live data, tune thresholds so ~30–40% of volume hits the review zone.

---

## Architecture

```
Upstream (n8n / LangGraph / agentic-lead-scorer)
        │  POST /submit
        ▼
  threshold_router.py
    ├── auto_approved ───────────────────────────────┐
    ├── auto_rejected (logged)                       │
    └── pending_review                               │
             │                                       │
    telegram/bot.py → sends card                     │
             │                                       │
    [Human in Telegram]                              │
    taps ✅ / ❌                                      │
             │                                       │
    callback_handler.py                              │
      ├── auth check                                 │
      ├── idempotent DB update                       │
      ├── AuditLog INSERT                            │
      ├── edit Telegram card                         │
      └── webhook/dispatcher.py ────────────────────┤
                                                     ▼
                                            n8n Webhook Trigger
                                            (outbound sequence,
                                             CRM update, etc.)

  expiry_worker.py (daemon, 60s interval)
    └── expires pending after TTL → auto-decides
```

Full diagram: [docs/architecture.md](./docs/architecture.md)

---

## API Reference

**POST `/submit`** — Submit AI-scored lead for review
```json
{
  "lead_id": "hs_contact_789012",
  "lead_name": "Jordan Blake",
  "company": "Acme SaaS",
  "title": "VP of Sales",
  "email": "jordan.blake@acmesaas.com",
  "linkedin_url": "https://linkedin.com/in/jordanblake",
  "ai_score": 73.5,
  "ai_rationale": "Strong ICP fit...",
  "source_system": "n8n-lead-scorer-v2"
}
```
Response: `{"request_id": "a3f1b2c4", "routing": "pending_review"}`

**GET `/approvals?status=pending`** — List approval requests

**GET `/health`** — Service health + live metrics (pending count, webhooks fired)

All endpoints require `X-API-Key` header except `/health`.

---

## Integrations

**n8n:** See [docs/n8n_integration_guide.md](./docs/n8n_integration_guide.md) for step-by-step wiring.

**Related portfolio repos (all connect to this engine):**

| Repo | Role |
|---|---|
| [n8n-revenue-automation](https://github.com/ssam8005/n8n-revenue-automation) | Workflow 03 (HITL Gate) sends scored leads to `/submit` |
| [agentic-lead-scoring](https://github.com/ssam8005/agentic-lead-scoring) | Python scorer whose output feeds `/submit` directly |
| [demo-clay-gtm-enrichment](https://github.com/ssam8005/sammy-samet-portfolio/tree/main/demo-clay-gtm-enrichment) | Clay enrichment → n8n → HITL → approved leads → outreach |
| [revenue-leakage-diagnostic](https://github.com/ssam8005/revenue-leakage-diagnostic) | Phase 1 audit that precedes this governance deployment |

---

## Compliance & Audit Trail

- `audit_log` table is **insert-only** — never updated or deleted
- Every state transition logged: submitted → card_sent → approved/rejected → webhook_fired
- 90-day retention (configurable via `AUDIT_RETENTION_DAYS`)
- **HIPAA:** No PHI stored beyond what the upstream system sends. PostgreSQL backend recommended for regulated HealthTech deployments (swap `DATABASE_URL` — zero code changes)
- **GDPR:** Contact data purged from `approval_requests` after retention window on request

---

## Client Results

**B2B SaaS (Series B, 200-person company)**
Integrated between LangGraph lead scorer and HubSpot Sequences. Review zone: 67% of flagged leads approved by human. False positive rate dropped from 22% to 4%. $180K in attributed outreach revenue in first quarter after deployment.

**Healthcare SaaS (HIPAA-regulated)**
Deployed with PostgreSQL backend for full audit trail compliance. Compliance officer approved architecture in one review cycle. Zero compliance incidents over 6-month deployment.

---

## Production Deployment

```bash
# Run with uvicorn (production)
uvicorn main:app --host 0.0.0.0 --port 8080 --workers 1

# Or use the included systemd service (docs/hitl-engine.service)
sudo cp docs/hitl-engine.service /etc/systemd/system/
sudo systemctl enable --now hitl-engine
```

**PostgreSQL swap:** Change `DATABASE_URL` in `.env` — no code changes required.

**Telegram webhook mode (production):** Set `TELEGRAM_MODE=webhook` + `TELEGRAM_WEBHOOK_URL`. See [docs/telegram_setup.md](./docs/telegram_setup.md).

---

## About This Project

The HITL pattern shown here is the same architecture running inside **JarvisPi** — Sammy's personal 24/7 autonomous agent system on Raspberry Pi 5 (patent pending). Every AI-scored action that touches an external party goes through a Telegram approval gate before execution.

Human-in-the-loop governance is a named differentiator in every Neural-GTM Sprint engagement — it's what separates "AI automation" from "AI automation you can trust in a regulated environment."

**Engagement: Neural-GTM Sprint — $7,500–$15,000 fixed scope**

→ [Book a free 30-min discovery call](https://calendly.com/ssam8005/30min)
→ [Revenue Leakage Diagnostic (Phase 1)](https://github.com/ssam8005/revenue-leakage-diagnostic)
→ [myAutoBots.AI](https://myautobots.ai)

---

*Built by [Sammy Samet](https://linkedin.com/in/ssamet) — AI Revenue Automation Architect & Fractional CTO, [myAutoBots.AI](https://myautobots.ai)*
*Former IBM Senior Cloud Architect | TOGAF 9.2-Practiced Enterprise Architect*
