# HITL Approval Engine — Architecture

## System Flow

```
Upstream AI System (n8n / LangGraph / agentic-lead-scorer)
        │
        │  POST /submit  {lead data + ai_score}
        │  Header: X-API-Key
        ▼
┌─────────────────────────────────────────────────┐
│            HITL Approval Engine                 │
│                                                 │
│  api/routes/submissions.py                      │
│       ↓                                         │
│  scoring/threshold_router.py                    │
│    ├─ score >= 85 → AUTO-APPROVE ───────────────┼──┐
│    ├─ score <= 30 → AUTO-REJECT  (logged only)  │  │
│    └─ 30 < score < 85 → REVIEW ZONE            │  │
│                │                                │  │
│  telegram/bot.py                                │  │
│    └─ sendMessage (card + ✅/❌ buttons)         │  │
│         │                                       │  │
│         ▼                                       │  │
│  [Human Reviewer in Telegram]                   │  │
│    taps ✅ Approve or ❌ Reject                  │  │
│         │                                       │  │
│  telegram/callback_handler.py                   │  │
│    ├─ auth check (TELEGRAM_CHAT_ID only)        │  │
│    ├─ idempotent status update                  │  │
│    ├─ AuditLog INSERT (immutable)               │  │
│    ├─ edit Telegram card (remove buttons)       │  │
│    └─ on approve → webhook/dispatcher.py ───────┼──┤
│                                                 │  │
│  workers/expiry_worker.py (daemon thread)       │  │
│    └─ expires pending after TTL ────────────────┼──┤
│                                                 │  │
│  database/                                      │  │
│    approval_requests  (mutable lifecycle)       │  │
│    audit_log          (insert-only, HIPAA)      │  │
└─────────────────────────────────────────────────┘  │
                                                     │
                                                     ▼
                                          ┌────────────────────┐
                                          │  n8n Webhook       │
                                          │  (outbound seq,    │
                                          │   CRM update, etc) │
                                          └────────────────────┘
```

## Component Responsibilities

| Component | Responsibility |
|---|---|
| `api/routes/submissions.py` | Receive AI decision, persist, route, return 202 immediately |
| `scoring/threshold_router.py` | Classify score into auto-approve / review / auto-reject zone |
| `telegram/card_formatter.py` | Build structured approval card with score badge + all lead context |
| `telegram/bot.py` | Send card, handle polling loop, edit card on decision |
| `telegram/callback_handler.py` | Process button taps: auth, idempotent update, audit, webhook |
| `webhook/dispatcher.py` | POST to n8n with 3-attempt retry and `X-Webhook-Secret` auth |
| `workers/expiry_worker.py` | Expire and auto-decide TTL-exceeded pending requests |
| `database/models.py` | `ApprovalRequest` (mutable) + `AuditLog` (insert-only, compliance) |

## Threshold Zones

| Zone | Default Score | Action | Human Review |
|---|---|---|---|
| Auto-Approve | ≥ 85 | Webhook fires immediately | No (FYI Telegram only) |
| Review | 31–84 | Telegram card + buttons | Yes |
| Auto-Reject | ≤ 30 | Logged, discarded | No |

Tune thresholds via `.env` after 30 days of live data. Target: ~30–40% of volume in the review zone.
