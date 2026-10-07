# Sprint 2 delivery bar

## Jira scope

Stories: N3-20 through N3-25, N3-31 through N3-34. Sprint 2 subtasks: N3-92 through N3-114. N3-20 is the parent for three Sprint 2 subtasks, although its Jira description omits the Sprint 2 label.

## Definition of Done

A story is done only when every Jira acceptance criterion has reproducible evidence and all of these checks pass:

- Server-side validation and authorization enforce the rule; tenant data remains isolated in API and PostgreSQL RLS.
- Data changes that belong together commit or roll back together. Schema changes have a reversible Alembic migration.
- Automated backend tests cover success, invalid input, cross-organization access, and failure/rollback paths where applicable.
- The UI has loading, empty, and error states; labels errors beside fields; prevents duplicate submission; and supports keyboard use. Review the desktop layout at 16:9.
- User-facing screens show real API data only. No simulated records, invented metrics, or architecture claims presented as live status.
- Changed API and user flows are documented. Local checks and the PR checks must pass before a story is marked done. Mobile validation is outside this desktop-only review.

## UI reference

Keep the existing `main` interface as the visual reference: retain its green palette, typography, sidebar, tables, and forms. Make targeted readability fixes only; do not add a UI library or introduce a new design system. Review desktop at 16:9. Keep visible focus, labels, and readable contrast. Hash serialization follows [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html).

## Evidence map

- N3-20/21: RFC 8785 canonical hash-chain tests, transaction rollback, database append-only permission tests, and README rule.
- N3-22: valid, tampered, missing-event, and direct SQL edit/delete verification tests; 1,000-event verification under one second; batched organization-name query; real timeline and integrity warning. Inspector verification is saved as an append-only, tenant-scoped record with timestamp and recent-check history (`POST/GET /api/v1/events/lots/{lot_id}/integrity-checks`).
- N3-23: 200-event history request under two seconds with a bounded SQL SELECT count, including organization names.
- N3-24/25: sender/recipient workflow, duplicate/self handover rejection, atomic accept/reject tests, pending inbox UI and sidebar count; lot detail links to its handover form and current request.
- N3-31/32/33/34: product permission/uniqueness tests, 10,000-code collision test, field validation, disabled-while-saving forms, cursor/search/filter tests, and real lot/product screens. Lot codes open a dedicated detail page with event history.

## Current status

- Main sync commit: `e412f82` includes upstream `main` at `a02d6e0`; PR [#9](https://github.com/nhom-3-cnttk23c/truy-xuat-nguon-goc-chuoi-lanh-nong-san/pull/9) is open.
- Jira: 2 of 33 Sprint 2 items are Done; the remaining 31 are In Progress while the PR awaits review.
- Local verification: 64 backend tests, Ruff, compileall, frontend lint/build, and migration upgrade/downgrade/re-upgrade passed. Browser flow checks ran at 1280×720. GitHub has not returned workflow/status checks for `e412f82` yet.
- Mobile checks were not run, per the desktop-only request.
