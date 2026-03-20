# HydroServer Deployment with Docker Compose

This guide describes how to deploy **HydroServer** using Docker Compose.
HydroServer releases are distributed as Docker images via [GitHub Container Registry (GHCR)](https://ghcr.io).

---

## Prerequisites

Before you begin, ensure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Docker Compose Setup

Below is a minimal `docker-compose.yml` example that will help you get started with a HydroServer deployment.

- Note: This example is intended to get you started, but is not ready to run. You should extend and modify this configuration as needed.

```yaml
services:
  hydroserver-base: &hydroserver_base
    image: ghcr.io/hydroserver2/hydroserver-api-services:latest
    environment:
      PROXY_BASE_URL: https://hydroserver.example.com
      SECRET_KEY: changeme
      DATABASE_URL: postgres://hydroserver:changeme@database:5432/hydroserver
    volumes:
      - static:/app/static
      - media:/app/media

  hydroserver-web:
    <<: *hydroserver_base
    restart: unless-stopped
    ports:
      - "8000:8000"
    depends_on:
      database:
        condition: service_healthy
      hydroserver-init:
        condition: service_completed_successfully
    command: >
      sh -c "gunicorn --bind 0.0.0.0:8000 --workers 3 hydroserver.wsgi:application"
    
  hydroserver-init:
    <<: *hydroserver_base
    depends_on:
      database:
        condition: service_healthy
    command: >
      sh -c "python manage.py migrate &&
             python manage.py setup_admin_user &&
             python manage.py load_default_data &&
             python manage.py collectstatic --noinput"
    restart: "no"

  database:
    image: postgres:17
    restart: unless-stopped
    environment:
      POSTGRES_DB: hydroserver
      POSTGRES_USER: hydroserver
      POSTGRES_PASSWORD: changeme
    volumes:
      - db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hydroserver"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  db:
  static:
  media:
```

For a more in-depth guide on how to use Docker Compose, visit their [documentation page](https://docs.docker.com/compose/).

## Environment Variables

There are several environment variables that can be used to configure HydroServer:
- **`PROXY_BASE_URL`** – The domain name for HydroServer, including the protocol (e.g., `https://yourdomain.com`).
- **`DATABASE_URL`** _(Optional)_ – The PostgreSQL database URL HydroServer will connect to.
  *Format:* `postgresql://{user}:{password}@{host}:{port}/{database}`
- **`SMTP_URL`** – Required for email notifications (account verification, password reset).  
  *Format:* `smtps://{user}:{password}@{host}:{port}`
- **`DEBUG`** _(Optional, default: `True`)_ – Set to `True` for non-production deployments.
- **`ACCOUNT_SIGNUP_ENABLED`** _(Optional, default: `False`)_ – If `False`, admins must create user accounts.
- **`ACCOUNT_OWNERSHIP_ENABLED`** _(Optional, default: `False`)_ – If `False`, users cannot create new workspaces.
- **`SOCIALACCOUNT_SIGNUP_ONLY`** _(Optional, default: `False`)_ – If `True`, only third-party identity providers can be used for signup.
- **`ENABLE_AUDITS`** _(Optional, default: `False`)_ – If `True`, HydroServer records database audit logs.

## Persistent Data

The example compose file defines three named volumes:
- **`db`** -> Stores PostgreSQL data.
- **`static`** -> Stores Django static files.
- **`media`** -> Stores HydroServer media files (photos).

In a production environment, static and media files should not be served directly by HydroServer. A separate service
such as **NGINX** can be set up to route traffic to HydroServer and serve these files from `/static/` and `/media/` 
respectively.

## Configure HydroServer

Once HydroServer is set up and running, there are additional configuration settings you can manage through the admin dashboard.

1. Log in to the HydroServer admin dashboard.
2. Go to **Sites** > **example.com** and update the default domain to match your HydroServer domain.
3. Go to **Web** to configure additional website settings.
   - **Instance Configuration**: Customize the HydroServer `About` page to add information about your organization.
   - **Analytics Configuration**: Optionally enable [Microsoft Clarity](https://clarity.microsoft.com/) for your instance.
   - **Map Configuration**: Customize the default map layers, view, geospatial, and elevation services.
   - **Map Layers**: Add additional map layer options for pages that use maps.
   - **Contact Information**: Add additional contact information for your organization to be displayed on the `About` page.
4. Navigate to **Social Applications** > **Add Social Application** to register identity providers (e.g., Google, HydroShare).
   - Select a provider from the list of supported providers.
   - Choose a unique ID and name for the provider.
   - Enter the client ID/key and secret key you received from the provider.
   - Enter optional JSON settings for the provider
     - **allowSignUp**: (true/false) — Controls whether this provider can be used for user sign up and login.
     - **allowConnection**: (true/false) — Controls whether users can connect to existing HydroServer accounts.
   - Select the default site to allow the provider to authenticate users for.
5. Populate the following models with default data you want available to all users, or load the preset defaults by clicking **Load Default Data** for each model:
   - Roles
   - Observed Properties
   - Processing Levels
   - Result Qualifiers
   - Sensors
   - Units
6. To configure HydroShare archival, do the following:
   - Configure HydroShare as an identity provider under **Social Applications**.
   - Add the following settings block to the HydroShare social application record:
     ```json
     {
       "allowSignUp": false, 
       "allowConnection": true
     }
     ```
   - Navigate to **Orchestration Systems** > **Add Orchestration System** and create a new record with the name "HydroShare Archival Manager" and type "HydroShare".
     - Note: This HydroShare archival setup method is temporary and will be deprecated in a future release.