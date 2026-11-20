# Setting Up a Development Environment

This guide will walk you through setting up HydroServer for local development.

::: tip Contributing
This guide is for setting up a local development instance of HydroServer which may be useful if you fork our repository and need to modify code. HydroServer is open source, and if you'd like to contribute directly to our repository, checkout our [`contributing guide.`](https://github.com/hydroserver2/hydroserver/blob/main/CONTRIBUTING.md)
:::

## Prerequisites

Before starting, make sure you have the following software installed on your machine:
- Python 3.14+
- Docker
- Node.js: The frontend uses various Node.js libraries. Check the package.json for specific version requirements.
- npm (typically bundled with Node.js): This is required to install the project's dependencies.

## NGINX Reverse Proxy and Development Database

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hydroserver2/hydroserver.git
   cd hydroserver/deploy/dev
   ```
2. Create environment variables for static and media file paths. The default locations of these folders should be `/static` and `/media` within the `hydroserver` project folder.
   Mac/Linux:
   ```bash
   export HS_MEDIAFILES="/path/to/media"
   export HS_STATICFILES="/path/to/static"
   ```
   Windows:
   ```cmd
   set HS_MEDIAFILES=C:\path\to\media
   set HS_STATICFILES=C:\path\to\static
   ```
3. Start Docker containers. All services can be accessed in a browser at `http://localhost`.
   ```bash
   docker compose --file "docker-compose.yaml" up
   ```
   The bundled NGINX config proxies `/.well-known/`, `/identity/`, `/accounts/`, `/admin/`, and `/api/` to Django so the local OIDC authorization flow works through `http://localhost`.

## HydroServer Django Backend

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hydroserver2/hydroserver.git
   cd hydroserver
   ```
2. Install the Python dependencies:
   ```bash
   pip install -r django/requirements.txt
   pip install -e packages/hydroserverpy
   ```
3. Perform database migrations and collect static files:
   ```bash
   ./scripts/dev-api-command manage.py migrate
   ./scripts/dev-api-command manage.py collectstatic --noinput
   ```
4. Create an admin user:
   ```bash
   ./scripts/dev-api-command manage.py createsuperuser
   ```
5. Start the Django development web server:
   ```bash
   ./scripts/dev-api-command manage.py runserver 127.0.0.1:8000
   ```

If you need OIDC identity provider features (discovery, authorize, token, and JWKS endpoints), generate a
signing key first:
```bash
openssl genpkey -algorithm RSA -out django/dev_oidc_private_key.pem -pkeyopt rsa_keygen_bits:2048
```

## HydroServer Frontend

### Data Management App

1. Navigate to `apps/data-management` and install the required packages:
   ```bash
   npm install
   ```
2. Create a .env file and update variables as needed. For getting started, the default settings should be sufficient.
3. Run the application in developer mode:
   ```bash
   npm run dev
   ```
4. Open `http://localhost`. The reverse proxy forwards frontend requests to Vite and backend requests, including the OIDC endpoints, to Django.

### QC App

1. Navigate to `apps/qc-app` and install the required packages:
   ```bash
   npm install
   ```
2. Run the application in developer mode:
   ```bash
   npm run dev
   ```
3. Open `http://localhost/qc`. The reverse proxy forwards these requests to the QC app's Vite server; no
   separate environment configuration is needed since backend requests are already routed through NGINX.
