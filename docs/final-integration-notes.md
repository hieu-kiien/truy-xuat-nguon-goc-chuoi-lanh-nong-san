# Final integration notes

This integration branch consolidates the UI/accessibility fixes and demo-auth/CI hardening work before merging to `main`.

## Included

- Responsive topbar/sidebar/table behavior and mobile layout fixes.
- Keyboard accessibility, focus states, reduced-motion support, and readable typography/contrast.
- Correct demo SHA-256 chain values and tamper simulation.
- Dependency-free integrity benchmark executed by CI.
- Demo login without a reusable public password; demo mode is restricted to explicit development/staging environments.
- Least-privilege PostgreSQL application role and RLS grant reconciliation for existing databases.
- Staging CORS restriction, static security headers/CSP, health check, and runtime version alignment.
- CI coverage for Ruff formatting/lint, Alembic migrations, Pytest, integrity tests, frontend lint/build, and Docker image builds.

## Environment-dependent items

GitHub Actions must be enabled for the repository for PR checks to run. Render deployment must also permit the database owner account to create/update the least-privilege `ttcs_app` role during startup. These are external platform settings rather than repository-code changes.
