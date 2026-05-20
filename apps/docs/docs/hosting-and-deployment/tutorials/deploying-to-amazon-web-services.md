# Amazon Web Services Quick Start Tutorial

The following tutorial will walk you through setting up HydroServer in Amazon Web Services. This is intended as a
**demonstration deployment** and will not be fully production-ready out of the box. This example will require 
customization to meet your organization’s operational, security, and scalability requirements. Before selecting a 
deployment platform, ensure you are familiar with the Amazon Web Service’s best practices and recommended approaches 
for running services in production.

## Deploy to Amazon Web Services (AWS) with Terraform

::: warning AWS App Runner Deprecated
As of April 30, 2026, AWS App Runner will no longer be available for new AWS customers. This tutorial will be updated
to use AWS ECS Express as a replacement service in the future.
:::

This tutorial provides instructions for deploying a demo HydroServer environment using 
[**Amazon Web Services (AWS)**](https://aws.amazon.com) resources provisioned with 
[**Terraform**](https://developer.hashicorp.com/terraform/docs). The deployment includes configuration of 
[**App Runner**](https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html), 
[**Relational Database Service (RDS)**](https://docs.aws.amazon.com/rds/), and other required AWS services.

Before proceeding, ensure you have:

- Access to an AWS account with sufficient permissions to provision the necessary resources.
- The following software installed and configured locally:
  - [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
  - [Terraform CLI](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)

Familiarity with Terraform, AWS services, and security best practices is recommended.

An example Terraform configuration demonstrating a simple HydroServer deployment on AWS is provided 
[here](https://github.com/hydroserver2/hydroserver/blob/main/apps/docs/docs/hosting-and-deployment/tutorials/examples/terraform-aws/main.tf).
This configuration performs the following tasks:

- Pulls the latest HydroServer release image from 
  [**GitHub Container Registry (GHCR)**](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
  and pushes it to [**AWS Elastic Container Registry (ECR)**](https://docs.aws.amazon.com/ecr/).   
- Provisions an RDS instance running PostgreSQL for HydroServer.
- Provisions an App Runner service, service account, and environment variables for HydroServer.

To deploy the services, navigate to the directory containing the `main.tf` file and run:

```bash
terraform init
terraform apply -var "region=your-aws-region"
```

Upon successful completion, Terraform will output a URL and admin user credentials you can use to access your deployed 
HydroServer instance.

To stop and tear down the service infrastructure, run:

```bash
terraform destroy -var "region=your-aws-region"
```

For more information, see the [AWS CLI documentation](https://docs.aws.amazon.com/cli/).