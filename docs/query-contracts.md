# Query Contracts for AppSmith Pages

These are the SQL entry points that AppSmith pages will consume. Each contract defines the expected input parameters, output columns, and source object in Postgres.

## Status

| Contract | Source Object | Status |
| :--- | :--- | :--- |
| Member Search | TBD (new view or parameterized query) | 🔲 Not started |
| Member Detail | TBD (new view by `raw_member_id`) | 🔲 Not started |
| Batch Summary | `vw_signup_batches_summary` | ✅ Exists |
| Batch Items | `vw_signup_batch_items` | ✅ Exists |
| Batch Consolidated | `vw_signup_batch_consolidated` | ✅ Exists |
| Best Contact | `resolve_best_contact_row(...)` | ✅ Exists |
| Best Contacts View | `vw_best_current_contacts` | ✅ Exists |
| Global Settings | `global_settings` table | ✅ Exists |
| Email Templates | `email_templates` table | ✅ Exists |
| Match Review | Match-review views | ✅ Exists |

## Contracts

### Member Search

**Input**: `search_term` (text), `year` (integer, optional)

**Expected output columns**:
| Column | Type | Notes |
| :--- | :--- | :--- |
| `raw_member_id` | integer | Hidden in UI, used for navigation |
| `first_name` | text | |
| `last_name` | text | |
| `email` | text | |
| `membership` | text | Product/membership type |
| `signup_status` | text | New / Processing / Complete / None |
| `has_signup` | boolean | Whether a signup record exists |

**Source**: Needs a new parameterized query or view. Should leverage `resolve_best_contact_row()` for address resolution.

---

### Member Detail (by raw_member_id)

**Input**: `raw_member_id` (integer)

**Expected output columns**:
| Column | Type | Notes |
| :--- | :--- | :--- |
| `raw_member_id` | integer | |
| `first_name` | text | |
| `last_name` | text | |
| `email` | text | |
| `membership` | text | |
| `age` | text | |
| `address_1` | text | Via best contact resolution |
| `address_2` | text | |
| `address_3` | text | |
| `town` | text | |
| `postcode` | text | |
| `signup_rows` | jsonb or separate query | Related signups |
| `contact_rows` | jsonb or separate query | Matched contacts |

**Source**: Needs a new view or function. May need multiple queries (member + related signups + related contacts).

---

### Batch Summary

**Input**: None (returns all batches)

**Source**: `vw_signup_batches_summary` (exists)

---

### Batch Items

**Input**: `batch_id` (integer)

**Source**: `vw_signup_batch_items` filtered by `batch_id` (exists)

---

### Batch Consolidated

**Input**: `batch_id` (integer)

**Source**: `vw_signup_batch_consolidated` filtered by `batch_id` (exists)

---

### Global Settings

**Input**: None (single-row table)

**Source**: `global_settings` table (exists)

**Mutations**: Direct UPDATE via AppSmith query

---

### Email Templates

**Input**: None (returns all templates)

**Source**: `email_templates` table (exists)

**Mutations**: Direct INSERT/UPDATE/DELETE via AppSmith queries
