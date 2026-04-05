# AppSmith Backup: Teams Management Page

Since AppSmith configuration is stored internally in its database until exported, this file serves as a backup of the queries and configuration built for the **Avondale Admin -> Teams** page.

## 1. `GetTeams` (SQL)
**Datasource:** `homedb`
```sql
SELECT * FROM public.vw_team_management_summary ORDER BY team_name ASC;
```

## 2. `GetTeamPlayers` (SQL)
**Datasource:** `homedb`
```sql
SELECT * FROM public.vw_appsmith_team_player_matching 
WHERE team_id = {{TableTeams.selectedRow.team_id}} 
ORDER BY sort_order ASC;
```
*Note: Configured to run automatically when `TableTeams` row is selected via `onRowSelected` UI event.*

## 3. `GetMailoutJob` (SQL)
**Datasource:** `homedb`
```sql
SELECT public.fn_get_team_mailout_job({{TableTeams.selectedRow.team_id}}) AS job;
```

## 4. `SendMailout` (REST API)
**Method:** POST
**URL:** `http://n8n:5678/webhook/send-team-captain-contact-lists`
**Body (JSON):**
```json
{
  "jobs": [
    {{GetMailoutJob.data[0].job}}
  ],
  "delivery_mode": "{{SelectDeliveryMode.selectedOptionValue || 'test'}}"
}
```

---
## UI Widgets & Bindings

### `SelectDeliveryMode` (Select Widget)
*Placed near the 'Send Captain Email' button to control delivery behavior natively.*
- **Options**:
  ```json
  [
    { "label": "Test Mode", "value": "test" },
    { "label": "Production Mode", "value": "production" }
  ]
  ```
- **Default Selected Value**: `"test"`

## 5. `UpdatePlayer` (SQL)
**Datasource:** `homedb`
```sql
SELECT public.fn_update_team_player(
  {{TablePlayers.updatedRow.team_player_id}}::bigint,
  {{TablePlayers.updatedRow.source_name}},
  {{TablePlayers.updatedRow.is_captain}}::boolean
);
```
*Note: Tied to `TablePlayers` inline editing `onSave` event. On success it runs `GetTeamPlayers`.*

## 6. `AddPlayer` (SQL)
**Datasource:** `homedb`
```sql
SELECT public.fn_add_team_player(
  {{TableTeams.selectedRow.team_id}}::bigint,
  'New Player',
  false
);
```
*Note: Tied to the 'Add Player' button. On success it runs `GetTeamPlayers`.*

## 7. `RemovePlayer` (SQL)
**Datasource:** `homedb`
```sql
SELECT public.fn_remove_team_player(
  {{TablePlayers.selectedRow.team_player_id}}::bigint
);
```
*Note: Tied to the 'Remove Player' button. On success it runs `GetTeamPlayers`.*

---
**To perform a full App Backup:**
1. Go to the AppSmith editor UI.
2. Click the dropdown next to the app name ("Avondale Admin") in the top center of the screen.
3. Select **"Export application"**.
4. Save the resulting JSON file into local version control.
