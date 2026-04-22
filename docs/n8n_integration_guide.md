# n8n Integration Guide

Connect the HITL Approval Engine to your n8n workflow stack in 3 steps.

## Step 1: Submit scored leads from n8n

In any n8n workflow where leads are scored, add an **HTTP Request** node after the scoring step:

- **Method:** POST
- **URL:** `http://your-server:8080/submit`
- **Auth:** Header — `X-API-Key: your_api_secret_key`
- **Body (JSON):**

```json
{
  "lead_id": "={{ $json.hs_contact_id }}",
  "lead_name": "={{ $json.firstname }} {{ $json.lastname }}",
  "company": "={{ $json.company }}",
  "title": "={{ $json.jobtitle }}",
  "email": "={{ $json.email }}",
  "ai_score": "={{ $json.icp_score }}",
  "ai_rationale": "={{ $json.score_rationale }}",
  "source_system": "n8n-lead-scorer-v1"
}
```

See `sample_payloads/n8n_trigger_example.json` for the complete node config.

## Step 2: Receive the approved-lead webhook in n8n

1. Create a new n8n workflow
2. Add a **Webhook Trigger** node — copy the production URL
3. Set `N8N_WEBHOOK_URL` in your `.env` to that webhook URL
4. Add `N8N_WEBHOOK_SECRET` in `.env` — set the same value in n8n as a Header Auth credential
5. The webhook receives this payload on every human approval:

```json
{
  "event": "lead_approved",
  "request_id": "a3f1b2c4",
  "lead_id": "hs_contact_789012",
  "lead_name": "Jordan Blake",
  "company": "Acme SaaS",
  "email": "jordan.blake@acmesaas.com",
  "ai_score": 73.5,
  "approved_by": "sammy_tg_username",
  "approved_at": "2026-04-21T14:32:00Z",
  "source_system": "n8n-lead-scorer-v1"
}
```

## Step 3: Connect to outbound sequence

After the Webhook Trigger, add your outbound action:
- **Instantly.ai / Lemlist:** Add contact to sequence via API node
- **HubSpot:** Create Contact + enroll in sequence via HubSpot node
- **Slack:** Post to `#approved-leads` channel

## Related Repos

- [n8n-revenue-automation](https://github.com/ssam8005/n8n-revenue-automation) — Full workflow library (workflows 01-05 connect to this engine)
- [agentic-lead-scoring](https://github.com/ssam8005/agentic-lead-scoring) — Python scorer whose output feeds `/submit`
- [demo-clay-gtm-enrichment](https://github.com/ssam8005/sammy-samet-portfolio/tree/main/demo-clay-gtm-enrichment) — Clay enrichment pipeline whose webhook-receiver feeds n8n → this engine
