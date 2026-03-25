# Development Setup

This guide will walk you through setting up HydroServer for local development.

::: tip Contributing
This guide is for setting up a local development instance of HydroServer which may be useful if you fork our repository and need to modify code. HydroServer is open source, and if you'd like to contribute directly to our repository, checkout our [`contributing guide.`](https://github.com/hydroserver2/hydroserver/blob/main/CONTRIBUTING.md)
:::

## Prerequisites

Before starting, make sure you have the following software installed on your machine:
- Python 3.11+
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
2. Create environment variables for static and media file paths. The default locations of these folders should be `/static` and `/media` within the `hydroserver-api-services` project folder.
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
   ```
3. Install the Django Tailwind dependency once:
   ```bash
   cd django
   npm install
   cd ..
   ```
4. Perform database migrations and collect static files:
   ```bash
   ./scripts/dev-api-command manage.py migrate
   ./scripts/dev-api-command manage.py collectstatic --noinput
   ```
5. Load the default development data. This also registers the bundled OIDC clients.
   ```bash
   ./scripts/dev-api-command manage.py load_default_data
   ```
6. Start the development web server:
   ```bash
   ./scripts/dev-api-command manage.py runserver 127.0.0.1:8000
   ```
7. In a second terminal, start the Django Tailwind watcher for the server-rendered account and OIDC templates:
   ```bash
   ./scripts/dev-django-tailwind
   ```

`./scripts/dev-api-command` automatically creates `django/dev_oidc_private_key.pem` if it does not already exist, so local OIDC discovery, authorize, token, and JWKS endpoints work without any manual key setup.

## HydroServer Data Management App

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hydroserver2/hydroserver.git
   cd hydroserver/apps/data-management
   ```
2. Install the required packages:
   ```bash
   npm install
   ```
3. Run the application in developer mode:
   ```bash
   npm run dev
   ```
4. Open `http://localhost`. The reverse proxy forwards frontend requests to Vite and backend requests, including the OIDC endpoints, to Django.
