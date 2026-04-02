# Avondale AppSmith Admin

Internal admin application for the Avondale membership system, built in [AppSmith](https://www.appsmith.com/).

## Purpose

Replaces the current Metabase dashboard + n8n webhook HTML surface for operator-facing workflows including:

- Membership search and detail views
- Signup batch operations
- Manual batch item entry
- Database review / audit pages
- Global settings and template management

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  AppSmith   │────▶│  Postgres   │     │    n8n      │
│  (UI/CRUD)  │     │  (homedb)   │     │ (workflows) │
│             │────▶│             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       ▲
       └───── webhook calls ───────────────────┘
```

- **AppSmith** → direct SQL for reads and simple mutations
- **AppSmith → n8n** → webhook calls for multi-step actions (PDF generation, email sending, sync)
- **Postgres views/functions** → shared contract boundary

## Deployment

- **Server**: `192.168.1.237` (n8n server)
- **Port**: `8080`
- **URL**: `http://192.168.1.237:8080`
- **Data volume**: `appsmith_data` (Docker named volume)

## References

- [Master Implementation Plan](file:///mnt/c/dev/avondale-n8n/APPSMITH_IMPLEMENTATION_PLAN.md)
- [System Design](file:///mnt/c/dev/avondale-n8n/DESIGN.md)
- [Services List](file:///mnt/c/dev/avondale-n8n/SERVICES.md)
- [Page Map](docs/page-map.md)
- [Query Contracts](docs/query-contracts.md)
- [Decision Log](docs/decision-log.md)
