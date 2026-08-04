# Data Management End-to-End Tests

Playwright suite for the data-management frontend. Run it from this app directory:

```bash
npm run e2e
```

Playwright (`apps/data-management/playwright.config.ts`) starts everything the
suite needs:

- the Django API in `django` (on `http://127.0.0.1:18000`)
- this Vue app, built and previewed (on `http://127.0.0.1:14173`)
- an isolated database initialized by `e2e/scripts/ensure_e2e_database.py` and
  `python manage.py setup_e2e_data`

It requires local `postgres` and `redis` to be running. The runner is isolated
from normal local development and uses a dedicated `hydroserver_e2e` database.

Install the API's test dependencies from `django/requirements-test.txt`. The
base setup contains only product defaults such as controlled vocabularies and
default roles.

## Isolated scenarios

Before every test, `e2e/support/test.ts` asks the test-only Django endpoint for
a new factory-built scenario. It returns generated users, workspaces, sites,
datastreams, metadata, and orchestration IDs. The fixture deletes that scenario
after the test, including after failures and retries.

Scenario users use the password `HydroServer123!` and unique generated email
addresses for these roles:

- owner: primary workspace owner for CRUD flows
- editor and viewer: permission-focused collaborators
- unaffiliated: workspace-transfer target
- profile: profile-editing user with organization data
- delete-me: disposable account-deletion user

Do not add fixed database IDs to `e2e/support/fixtures.ts`. Add new records to
the scenario builder and return their generated IDs instead.

## Notes

- Most authenticated page tests use a scenario session cookie helper because the
  app login flow does not persist the session cookie reliably under browser
  automation. Browser login itself is still exercised through the UI.
- The visualization tests rely on the app honoring `VITE_APP_PROXY_BASE_URL` so
  the isolated Playwright API instance is used instead of the local dev port.
- The manual release checklist in
  `tests/manual/MANUAL_RELEASE_TESTING_CHECKLIST.md` complements this suite for
  external-system checks that are not deterministic in headless automation.
