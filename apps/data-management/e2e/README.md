# Data Management End-to-End Tests

Playwright suite for the data-management frontend. Run it from this app directory:

```bash
npm run e2e
```

Playwright (`apps/data-management/playwright.config.ts`) starts everything the
suite needs:

- the Django API in `django` (on `http://127.0.0.1:18000`)
- this Vue app, built and previewed (on `http://127.0.0.1:14173`)
- a deterministic seeded database created by
  `e2e/scripts/ensure_e2e_database.py` + `python manage.py setup_e2e_data`

It requires local `postgres` and `redis` to be running. The runner is isolated
from normal local development and uses a dedicated `hydroserver_e2e` database.

## Seeded users

All seeded users use the password `HydroServer123!`:

- `owner@example.com`: primary workspace owner for CRUD flows
- `viewer@example.com`: collaborator target
- `unaffiliated@example.com`: workspace-transfer target
- `profile@example.com`: profile-editing user with organization data
- `delete-me@example.com`: disposable account-deletion user

## Notes

- Most authenticated page tests use a seeded session cookie helper because the
  app login flow does not persist the session cookie reliably under browser
  automation. Browser login itself is still exercised through the UI.
- The visualization tests rely on the app honoring `VITE_APP_PROXY_BASE_URL` so
  the isolated Playwright API instance is used instead of the local dev port.
- The manual release checklist in
  `tests/manual/MANUAL_RELEASE_TESTING_CHECKLIST.md` complements this suite for
  external-system checks that are not deterministic in headless automation.
