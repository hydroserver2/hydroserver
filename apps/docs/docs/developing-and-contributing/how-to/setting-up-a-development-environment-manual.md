# Setting Up a Development Environment

This guide will walk you through setting up HydroServer for local development.

::: tip Contributing
This guide is for setting up a local development instance of HydroServer which may be useful if you fork our repository and need to modify code. HydroServer is open source, and if you'd like to contribute directly to our repository, checkout our [`contributing guide.`](https://github.com/hydroserver2/hydroserver/blob/main/CONTRIBUTING.md)
:::

## Prerequisites

- Python 3.14+
- Node.js and npm
- A PostgreSQL (17+) server reachable from your machine. This does **not** require Docker — a native
  install works fine — but if you'd like a quick disposable one:
  ```bash
  docker run -d --name hydroserver-postgres -p 5432:5432 \
    -e POSTGRES_USER=hsdbadmin -e POSTGRES_PASSWORD=admin -e POSTGRES_DB=hydroserver \
    postgres:17
  ```
  This configuration matches HydroServer's default `DATABASE_URL` setting.

## HydroServer Django Backend

1. Clone the repository and install the Python dependencies:
   ```bash
   git clone https://github.com/hydroserver2/hydroserver.git
   cd hydroserver
   pip install -r django/requirements.txt
   pip install -e packages/hydroserverpy
   ```
2. Optional — create `django/.env` from the template if you want to override any default settings (a
   different database, a non-default port, etc.):
   ```bash
   cp django/.env.example django/.env
   ```
3. Apply database migrations:
   ```bash
   cd django
   python manage.py migrate
   ```
4. Optional — create an admin account (only needed if you want to use `/admin`; regular signup works
   without this):
   ```bash
   python manage.py createsuperuser
   ```
5. Start the development server:
   ```bash
   python manage.py runserver 127.0.0.1:8000
   ```

## HydroServer Frontend

Each frontend app needs to be told directly where Django lives, via `VITE_APP_PROXY_BASE_URL` — otherwise
its dev server won't proxy `/api` requests anywhere and calls to the backend will fail.

### Data Management App

```bash
cd apps/data-management
npm install
echo "VITE_APP_PROXY_BASE_URL=http://127.0.0.1:8000" >> .env
npm run dev
```
Open `http://127.0.0.1:1203`.

### QC App

```bash
cd apps/qc-app
npm install
echo "VITE_APP_PROXY_BASE_URL=http://127.0.0.1:8000" >> .env
npm run dev
```
Open `http://127.0.0.1:5173`.

## Optional: Background Task Processing (Celery + Redis)

Only needed if you're working on orchestration (ETL tasks, monitoring tasks, data product tasks) —
everything else (auth, core API/CRUD, the SPAs) works without this.

1. Start Redis:
   ```bash
   docker run -d --name hydroserver-redis -p 6379:6379 redis:7
   ```
   (or a native install — Django's default `CELERY_BROKER_URL` already points at `redis://127.0.0.1:6379/0`,
   so no `.env` change needed if you use the default port.)
2. Run a worker with beat scheduler enabled:
   ```bash
   cd django
   celery -A hydroserver worker -B -l info
   ```

## Optional: Local Email Viewing

By default, `SMTP_URL` is unset and account-related emails (verification, password reset) print to the
console where `runserver` is running. If you'd rather view them in a real inbox UI, run something like 
[MailHog](https://github.com/mailhog/MailHog) or [Mailpit](https://github.com/axllent/mailpit) and 
set `SMTP_URL=smtp://127.0.0.1:1025` in `django/.env`.

## Optional: OpenID Connect Identity Provider

Only needed if you're testing the OIDC identity provider (discovery, authorize, token, and JWKS
endpoints). Generate a signing key:
```bash
cd django
openssl genpkey -algorithm RSA -out dev_oidc_private_key.pem -pkeyopt rsa_keygen_bits:2048
```
