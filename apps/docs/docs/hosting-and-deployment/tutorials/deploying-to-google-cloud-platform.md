# Google Cloud Platform Quick Start Tutorial

The following tutorial will walk you through setting up HydroServer in Google Cloud Platform. This is intended as a
**demonstration deployment** and will not be fully production-ready out of the box. This example will require 
customization to meet your organization’s operational, security, and scalability requirements. Before selecting a 
deployment platform, ensure you are familiar with the Google Cloud Platform’s best practices and recommended approaches 
for running services in production.

## Google Cloud Platform (GCP) with Terraform

This tutorial provides instructions for deploying a demo HydroServer environment using
[**Google Cloud Platform (GCP)**](https://cloud.google.com) resources provisioned with 
[**Terraform**](https://developer.hashicorp.com/terraform/docs). The deployment includes configuration of 
[**Cloud Run**](https://cloud.google.com/run/docs/overview/what-is-cloud-run), 
[**Cloud SQL**](https://cloud.google.com/sql), and other required AWS services.

Before proceeding, ensure you have:

- Access to a GCP project with sufficient permissions to provision the necessary resources.
- The following software installed and configured locally:
  - [gcloud CLI](https://cloud.google.com/sdk/docs/install)
  - [Terraform CLI](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)

Familiarity with Terraform, GCP services, and security best practices is recommended.

An example Terraform configuration demonstrating a simple HydroServer deployment on GCP is provided 
[here](https://github.com/hydroserver2/hydroserver/blob/main/apps/docs/docs/hosting-and-deployment/tutorials/examples/terraform-gcp/main.tf).
This configuration performs the following tasks:

- Pulls the latest HydroServer release image from 
  [**GitHub Container Registry (GHCR)**](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
  and pushes it to [**GCP Artifact Registry**](https://cloud.google.com/artifact-registry/docs).   
- Provisions a Cloud SQL instance running PostgreSQL for HydroServer.
- Provisions a Cloud Run service, service account, and environment variables for HydroServer.

To deploy the services, navigate to the directory containing the `main.tf` file and run:

```bash
terraform init
terraform apply -var "region=your-gcp-region" -var "project_id=your-gcp-project-id"
```

Upon successful completion, Terraform will output a URL and admin user credentials you can use to access your deployed 
HydroServer instance.

To stop and tear down the service infrastructure, run:

```bash
terraform destroy -var "region=your-gcp-region" -var "project_id=your-gcp-project-id"
```

For more information, see the [gcloud CLI documentation](https://cloud.google.com/sdk/gcloud).