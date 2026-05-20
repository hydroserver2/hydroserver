# Docker Compose Quick Start Tutorial

The following tutorial will walk you through setting up HydroServer with Docker Compose. This is intended as a
**demonstration deployment** and will not be fully production-ready out of the box. This example will require 
customization to meet your organization’s operational, security, and scalability requirements. Before selecting a 
deployment platform, ensure you are familiar with best practices and recommended approaches 
for running services in production.

## Docker Compose (Local or VM)

This tutorial provides instructions for deploying a demo HydroServer environment using Docker Compose on a local machine 
or virtual machine. The deployment includes configuration of a basic HydroServer web server alongside a PostgreSQL 
database, all defined in a Docker Compose file.

Before proceeding, ensure you have the following installed and configured locally:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Familiarity with Docker Compose concepts such as services, volumes, and environment variables is recommended.

An example configuration demonstrating how to deploy HydroServer with Docker Compose is provided 
[here](https://github.com/hydroserver2/hydroserver/blob/main/apps/docs/docs/hosting-and-deployment/tutorials/examples/docker-compose/docker-compose.yaml). 
This example configuration performs the following tasks:

- Pulls the latest HydroServer release image from 
  [**GitHub Container Registry (GHCR)**](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
  and runs it in a local container
- Deploys a PostgreSQL database container
- Defines persistent volumes for the database, static files, and media files

To start the services, navigate to the directory containing the `docker-compose.yml` file and run:

```bash
docker compose up
```

Upon successful completion, HydroServer will be available locally at localhost:8000.

To stop the service, run:

```bash
docker compose down
```

For more information, see the [Docker Compose CLI documentation](https://docs.docker.com/reference/cli/docker/compose/).