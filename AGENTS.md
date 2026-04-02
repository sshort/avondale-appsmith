# Agent Instructions for avondale-appsmith

This file contains specific instructions for AI agents working on this repository.

## Project Context

This is the **AppSmith admin application** for the Avondale membership system. It replaces the current Metabase + n8n webhook UI surface for operator-facing workflows.

### Key References
- **Master Plan**: [APPSMITH_IMPLEMENTATION_PLAN.md](file:///mnt/c/dev/avondale-n8n/APPSMITH_IMPLEMENTATION_PLAN.md) in avondale-n8n
- **System Design**: [DESIGN.md](file:///mnt/c/dev/avondale-n8n/DESIGN.md) in avondale-n8n
- **Services List**: [SERVICES.md](file:///mnt/c/dev/avondale-n8n/SERVICES.md) in avondale-n8n

## Project Management & Tracking

### Obsidian Kanban Board
- **File**: `/mnt/c/dev/avondale-notes/Dev Kanban.md`
- **Requirement**: Keep this board up to date for **significant functionality changes** and **large effort jobs**.
- **Process**:
    1. **New Card**: Create a new card if one doesn't exist for the task.
    2. **In Progress**: Move the card to `## In Progress` before starting the work.
    3. **Complete**: Move the card to `## Complete` and mark as `[x]` once the task is finished/verified.

## Architecture

### Split Responsibilities
- **AppSmith**: Operator-facing pages, search, detail views, batch operations, admin screens, direct DB queries
- **n8n**: Scheduled jobs, email parsing, sync, PDF generation, multi-step workflows with retries

### Data Access
- AppSmith connects directly to Postgres on `homedb` (`192.168.1.248:5432`)
- Use existing views/functions as the contract boundary (e.g. `vw_signup_batches_summary`, `resolve_best_contact_row()`)
- For actions needing n8n workflow execution, call n8n webhooks from AppSmith

### Key Principle
Do **not** rewrite business logic in AppSmith JS. Keep it in Postgres views/functions or n8n workflows where it already works.
