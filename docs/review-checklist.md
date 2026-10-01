# Review checklist

- [x] UI responsive/mobile fixes retained after integration.
- [x] Accessibility overrides loaded after base stylesheet.
- [x] Demo credentials removed from frontend/seed source.
- [x] Demo login disabled outside explicit development/staging environments.
- [x] Integrity canonical JSON/SHA-256/tamper test runnable with Node.
- [x] Runtime PostgreSQL role configured as least privilege with no BYPASSRLS.
- [x] Existing database grants reconciled through Alembic migration.
- [x] Staging CORS narrowed to the staging frontend.
- [x] CSP/security headers configured for static frontend.
- [x] Python/Node versions aligned across local, Docker and CI.
- [ ] GitHub Actions PR checks observed running (external repository setting currently blocks/does not create runs).
- [ ] Render deployment verified after merge (external platform execution).
