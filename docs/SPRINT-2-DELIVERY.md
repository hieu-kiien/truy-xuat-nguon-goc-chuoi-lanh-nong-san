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

Use a small, consistent token set for color, spacing, type, borders, and focus states, following [Material 3 color roles](https://m3.material.io/styles/color/the-color-system) and [typography](https://m3.material.io/styles/typography/applying-type). Target [WCAG 2.2 AA](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) for text contrast, keyboard access, focus visibility, and form labels. For field use in bright light, interactive controls should be at least 44px high with clear text and generous spacing. Hash serialization follows [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html).

## Evidence map

- N3-20/21: RFC 8785 canonical hash-chain tests, transaction rollback, database append-only permission tests, and README rule.
- N3-22: valid, tampered, missing-event, and direct SQL edit/delete verification tests; 1,000-event verification under one second; batched organization-name query; real timeline and integrity warning.
- N3-23: 200-event history request under two seconds with a bounded SQL SELECT count, including organization names.
- N3-24/25: sender/recipient workflow, duplicate/self handover rejection, atomic accept/reject tests, and pending inbox UI.
- N3-31/32/33/34: product permission/uniqueness tests, 10,000-code collision test, field validation, disabled-while-saving forms, cursor/search/filter tests, and real lot/product screens.
