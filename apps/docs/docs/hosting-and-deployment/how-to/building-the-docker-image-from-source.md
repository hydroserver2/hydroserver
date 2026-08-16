# Building the Docker Image from Source

HydroServer publishes a pre-built container image for every release to the
[**GitHub Container Registry**](https://github.com/hydroserver2/hydroserver/pkgs/container/hydroserver), which is the
recommended way to deploy HydroServer (see
[**Setting Up a Production Deployment**](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md)). This
guide is for building that same image yourself instead — useful if you're testing local changes, building from an
unreleased branch, or want to inspect the build process directly.

## Prerequisites

- [**Docker**](https://www.docker.com/) with [**BuildKit**](https://docs.docker.com/build/buildkit/) support. BuildKit
  has been the default builder since Docker Engine 23.0 — if you're on an older Docker installation, see the note in
  Step 2 below.
- Git.

## Step 1: Clone the repository

```bash
git clone https://github.com/hydroserver2/hydroserver.git
cd hydroserver
```

## Step 2: Set up a builder (older Docker installations only)

The Dockerfile uses a multi-platform-aware build stage for the frontend apps. If `docker buildx build` fails with an
error about parsing an empty platform, your Docker installation's default builder doesn't resolve this correctly.
Create a dedicated builder that does:

```bash
docker buildx create --name hydroserver-builder --driver docker-container --use
```

This is a one-time setup step. Once created and selected (`--use`), later `docker buildx build` commands will use it
automatically. If `docker buildx build` already works without this, you can skip this step.

## Step 3: Build the image

From the repository root:

```bash
docker buildx build --load -t hydroserver:local -f django/Dockerfile .
```

- **--load**  
  Loads the built image into your local Docker image store so it's usable with `docker run`. Without it, `buildx`
  only builds the image without making it available locally.

## Step 4: Apply database migrations

Run this once against the database your container will use:

```bash
docker run --rm -e DATABASE_URL="postgresql://hsdbadmin:admin@127.0.0.1:5432/hydroserver" hydroserver:local \
  python manage.py migrate
```

## Step 5: Run the container

```bash
docker run -p 8000:8000 -e DATABASE_URL="postgresql://hsdbadmin:admin@127.0.0.1:5432/hydroserver" hydroserver:local \
  gunicorn hydroserver.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Every setting other than `DATABASE_URL` falls back to its default in this example, which is enough to get a working
instance running locally. For the full list of supported environment variables and their production
recommendations, see
[**Setting Up a Production Deployment**](/hosting-and-deployment/how-to/setting-up-a-production-deployment.md).

After the server starts, visit `http://127.0.0.1:8000` in a browser to access HydroServer.