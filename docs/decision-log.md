# Decision Log: AppSmith vs n8n

Which functionality moves to AppSmith and which stays in n8n.

## Guiding Principles

1. **AppSmith** for operator-facing UI, search, detail views, direct DB reads/writes
2. **n8n** for scheduled jobs, multi-step workflows, external integrations, retries
3. **Postgres** remains the business logic home — views, functions, constraints

## Decisions

### Move to AppSmith ✅

| Feature | Reason |
| :--- | :--- |
| Membership search | Needs richer interaction than Metabase cards |
| Member detail page | Currently awkward webhook-generated HTML |
| Signup batch list | Needs action buttons, not just Metabase tables |
| Signup batch detail / member rows | Needs grouped views with inline actions |
| Manual batch item form | Better as a proper form with validation |
| Missing signup review | Needs drilldown and action buttons |
| Ambiguous/weak match review | Better filtering and row actions than Metabase |
| Global settings editor | Needs write capability, not Metabase view-only |
| Email templates editor | CRUD with preview |

### Keep in n8n ❌

| Feature | Reason |
| :--- | :--- |
| ClubSpark auth & export | External service, retries, session management |
| New member email parser | Gmail trigger + parsing logic |
| Sync local → cloud DB | Scheduled, multi-step |
| Membership snapshot capture | Scheduled |
| Label PDF generation | Gotenberg integration, file output |
| DL envelope PDF generation | Gotenberg integration, file output |
| No-address batch email send | Multi-step, email service integration |
| Batch creation workflow | Atomic SQL + audit, currently working well in n8n |
| Batch completion workflow | Atomic SQL + audit, currently working well in n8n |

### Hybrid (AppSmith triggers n8n) 🔀

| Feature | AppSmith Role | n8n Role |
| :--- | :--- | :--- |
| Batch actions (Labels, Envelopes) | Button in Batch Detail page | Webhook executes PDF generation |
| No-address emails | Button in Batch Detail page | Webhook executes email send |
| Create/Complete batch | Button in Signup Batches page | Webhook executes atomic SQL |
| Create missing signup | Button in Missing Signup page | Webhook executes capture logic |

## Open Decisions

- [ ] Should batch creation/completion move to direct AppSmith SQL, or keep as n8n webhook? (Recommendation: keep in n8n for now)
- [ ] Should `add-manual-batch-item` move to direct SQL, or keep n8n webhook? (Recommendation: evaluate complexity first)
