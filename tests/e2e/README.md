# End-to-End Tests

This directory contains the HydroServer browser-based end-to-end test suite.

The suite uses Playwright and runs against:

- the Django API in `django`
- the Vue app in `apps/data-management`
- a deterministic seeded database created by `python manage.py setup_e2e_data`

Seeded E2E users currently use the password `HydroServer123!`.
Dedicated seeded users:

- `owner@example.com`: primary workspace owner for CRUD flows
- `viewer@example.com`: collaborator target
- `unaffiliated@example.com`: workspace-transfer target
- `profile@example.com`: profile-editing user with organization data
- `delete-me@example.com`: disposable account-deletion user

The runner is isolated from normal local development:

- API: `http://127.0.0.1:18000`
- app: `http://127.0.0.1:14173`
- database: `hydroserver_e2e`

## Coverage

The initial suite covers the core workflows that are stable and valuable to gate:

- anonymous access control for protected routes
- login with a seeded user
- account onboarding for users with no workspaces
- profile editing and account deletion
- root navigation and about-page availability
- workspace creation from the shared workspace toolbar
- workspace edit validation, privacy changes, and deletion
- workspace collaborator add, edit, and removal
- public site details plus site photo/site/datastream CRUD on a seeded mutable site
- metadata page shell and tab availability
- representative workspace sensor CRUD
- visualization bootstrap, metadata modal actions, CSV/ZIP downloads, selected-only filtering, summary mode, and copied URL restore
- orchestration page loading with seeded workspace data
- pending workspace transfer visibility for the target user
- release-coverage mapping in `tests/e2e/release-matrix.yaml`

## Running Locally

1. Start local infrastructure required by the API:
   `postgres` and `redis`
2. Install the E2E dependencies:
   ```bash
   ./scripts/e2e install
   ```
3. Run the suite:
   ```bash
   ./scripts/e2e test
   ```

Playwright will start the API and the data-management app automatically. The API process creates and reseeds the dedicated `hydroserver_e2e` database before the suite starts.

For a full release-oriented regression pass from the repo root, run:

```bash
./scripts/release-test all
```

This executes:

- the API pytest suite
- the `hydroserverpy` pytest suite
- the browser E2E suite

## Notes

- Browser login is tested through the UI, but most authenticated page tests use a seeded session cookie helper because the current app login flow does not persist the session cookie reliably in the browser automation environment.
- The visualization tests rely on the app honoring `VITE_APP_PROXY_BASE_URL` for bootstrap requests so the isolated Playwright API instance is used instead of the default local dev port.
- `tests/e2e/release-matrix.yaml` is the source of truth for which release-test document cases are automated in Playwright, delegated to pytest, or still manual because they depend on external systems such as SDL or HydroShare.
