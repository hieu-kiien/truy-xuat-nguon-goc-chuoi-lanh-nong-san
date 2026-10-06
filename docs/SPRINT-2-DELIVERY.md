# Sprint 2 delivery bar

## Jira scope

Stories: N3-20 through N3-25, N3-31 through N3-34. Sprint 2 subtasks: N3-92 through N3-114. N3-20 is the parent for three Sprint 2 subtasks, although its Jira description omits the Sprint 2 label.

## Definition of Done

A story is done only when every Jira acceptance criterion has reproducible evidence and all of these checks pass:

- Server-side validation and authorization enforce the rule; tenant data remains isolated in API and PostgreSQL RLS.
- Data changes that belong together commit or roll back together. Schema changes have a reversible Alembic migration.
- Automated backend tests cover success, invalid input, cross-organization access, and failure/rollback paths where applicable.
- The UI has loading, empty, and error states; labels errors beside fields; prevents duplicate submission; and works by keyboard and on a 320px-wide viewport.
- User-facing screens show real API data only. No simulated records, invented metrics, or architecture claims presented as live status.
- Changed API and user flows are documented. CI passes, and desktop plus mobile browser checks leave no console errors.

## UI reference

Use a small, consistent token set for color, spacing, type, borders, and focus states, following Material Design 3's role-based tokens and type hierarchy. Target WCAG 2.2 AA for text contrast, keyboard access, focus visibility, and form labels. For field use in bright light, interactive controls should be at least 44px high with clear text and generous spacing.

## Evidence map

- N3-20/21: canonical hash-chain tests, transaction rollback, database append-only permission tests, and README rule.
- N3-22/23: valid/tampered/missing-event verification tests, batched organization-name query, real timeline and integrity warning.
- N3-24/25: sender/recipient workflow, duplicate/self handover rejection, atomic accept/reject tests, and pending inbox UI.
- N3-31/32/33/34: product permission/uniqueness tests, 10,000 generated-code test, field validation and duplicate-submit tests, and cursor/search/filter tests.
