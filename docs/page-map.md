# AppSmith Page Map

Navigation structure for the Avondale admin application.

## Pages

### Search
- **Purpose**: Primary member lookup
- **Features**: Search box with year filter, results table, per-row signup status, row-click navigation to Member Detail
- **Data**: Member search query returning `raw_member_id`, visible fields, signup status
- **Phase**: 4 (first migrated flow)

### Member Detail
- **Purpose**: Full view of a selected member
- **Features**: Member identity, resolved membership rows, matched signup rows, matched contact rows, best contact/address summary
- **Data**: Member detail query by `raw_member_id`
- **Phase**: 5

### Signup Batches
- **Purpose**: List and manage signup batches
- **Features**: Batch list with counts/totals/status, consolidated item totals, action buttons column
- **Data**: `vw_signup_batches_summary`
- **Phase**: 6

### Batch Detail
- **Purpose**: View members in a specific batch
- **Features**: Member rows, grouped/consolidated view, no-address email sent status, action controls
- **Data**: `vw_signup_batch_items`, `vw_signup_batch_consolidated`
- **Phase**: 6

### Manual Batch Item
- **Purpose**: Add a manual item to a batch
- **Features**: Form with batch_id, regular tags, parent tags, keys, notes
- **Execution**: n8n webhook call (keep existing `add-manual-batch-item` workflow)
- **Phase**: 5

### Missing Signup Capture
- **Purpose**: Create missing signup records
- **Features**: Review list of members without signup records, "create capture" action
- **Phase**: 7

### Database Review
- **Purpose**: Audit and review raw data quality
- **Features**: Ambiguous raw matches, weak name-only matches, latest raw match outcomes/audit
- **Data**: Match-review views
- **Phase**: 7

### Settings
- **Purpose**: Edit operational settings
- **Features**: `global_settings` CRUD, read/write separation, simple validation
- **Phase**: 8

### Templates
- **Purpose**: Manage email templates
- **Features**: `email_templates` CRUD
- **Phase**: 8

## Navigation Structure

```
┌───────────────────────────────────────────┐
│  Sidebar Navigation                       │
├───────────────────────────────────────────┤
│  🔍 Search                               │
│  📋 Signup Batches                        │
│  ──────────────────────                   │
│  📊 Database Review                       │
│  ⚙️  Settings                             │
│  📝 Templates                             │
└───────────────────────────────────────────┘
```

- **Search** → click row → **Member Detail** → action → **Manual Batch Item**
- **Signup Batches** → click row → **Batch Detail**
- Parameter passing between pages via URL query params or AppSmith store
