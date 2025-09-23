# Deploying HydroServer for Production

This guide provides an overview for deploying HydroServer in a production environment. It is intended to help system 
administrators and developers get started with setting up key infrastructure needed to run HydroServer reliably and at
scale based on their needs and use-cases. The guide includes an overview of required infrastructure, production
configuration settings, and several examples using Terraform and Docker Compose to help you get started on your chosen
deployment platform.

## HydroServer Required Infrastructure 

Each HydroServer release includes a [**container image**](https://github.com/hydroserver2/hydroserver-api-services/pkgs/container/hydroserver-api-services) 
that packages the core HydroServer website, APIs, and supporting services. This image follows the OCI (Open Container 
Initiative) standard and can be deployed on any platform that supports [**Docker**](https://www.docker.com/) or other 
OCI-compatible runtimes, including commercial cloud providers or local environments. The image comes pre-configured with 
[**Gunicorn**](https://docs.gunicorn.org/) as the web server for production use and can also be used to run 
administrative and deployment management commands.

HydroServer requires a [**PostgreSQL database (version 15 or higher)**](https://www.postgresql.org/) for data storage. 
At present, no specific PostgreSQL extensions are required, although you should ensure the database is accessible from 
the HydroServer deployment environment and configured with sufficient resources for your expected workload.

Because Gunicorn is not designed to serve static files, HydroServer’s static assets must be collected and served 
through a separate mechanism. Recommended approaches for serving static files will vary by platform and additional 
details and examples are provided below.

For user account management, HydroServer requires access to an external email server to send account verification and 
password reset emails. Alternatively, you may integrate third-party identity providers (e.g. 
[Google](https://cloud.google.com/identity-platform/docs/web/google)) for account creation and sign-in. When using 
third-party authentication exclusively, certain account management features—such as direct password resets via 
email—may not be required.

## Production Deployment Quick Start Examples

The following examples provide guidance for deploying HydroServer in production environments. These are intended as 
**demonstration deployments** and are not fully production-ready out of the box. Each example will require 
customization to meet your organization’s operational, security, and scalability requirements. Before selecting a 
deployment platform, ensure you are familiar with the platform’s best practices and recommended approaches for running 
services in production.

### Amazon Web Services (AWS) with Terraform

This section provides instructions for deploying a demo HydroServer environment using 
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
[here](https://github.com/hydroserver2/hydroserver/blob/main/docs/how-to/deployment/examples/terraform-aws/main.tf).
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

### Google Cloud Platform (GCP) with Terraform

This section provides instructions for deploying a demo HydroServer environment using
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
[here](https://github.com/hydroserver2/hydroserver/blob/main/docs/how-to/deployment/examples/terraform-gcp/main.tf).
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

### Docker Compose (Local or VM)

This section provides instructions for deploying a demo HydroServer environment using Docker Compose on a local machine 
or virtual machine. The deployment includes configuration of a basic HydroServer web server alongside a PostgreSQL 
database, all defined in a Docker Compose file.

Before proceeding, ensure you have the following installed and configured locally:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Familiarity with Docker Compose concepts such as services, volumes, and environment variables is recommended.

An example configuration demonstrating how to deploy HydroServer with Docker Compose is provided 
[here](https://github.com/hydroserver2/hydroserver/blob/main/docs/how-to/deployment/examples/docker-compose/docker-compose.yaml). 
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

## Preparing for Production Deployment

The example configurations provided in the previous section are intended for demonstration and evaluation purposes only.
For production use, additional configuration and infrastructure are strongly recommended.

### HydroServer Production Environment Variables

HydroServer’s Docker image supports the following environment variables for configuring a deployment:

- **DEPLOYMENT_BACKEND**  
  Platform where HydroServer static files are collected.  
  Example: `docker`, `aws`, `gcp`, `dev`

- **SECRET_KEY**  
  Secret used by Django to encrypt passwords and sign sessions. Must be securely generated and stored in production.  
  Example: See [Django docs](https://docs.djangoproject.com/en/5.2/ref/settings/#secret-key)

- **DEBUG**  
  Enables debug mode. Must be `False` in production.  
  Example: `True` / `False`

- **DEFAULT_SUPERUSER_EMAIL**  
  Email for the default admin user created with `python manage.py setup_admin_user`.  
  Example: `admin@example.com`

- **DEFAULT_SUPERUSER_PASSWORD**  
  Password for the default admin user.  
  Example: `securepassword123`

- **PROXY_BASE_URL**  
  Base URL for your HydroServer instance.  
  Example: `https://hydroserver.your-domain.com`

- **DATABASE_URL**  
  PostgreSQL connection string.  
  Example: `postgresql://hsdbadmin:securepassword123@127.0.0.1:5432/hydroserver`

- **ACCOUNT_SIGNUP_ENABLED**  
  Whether public account creation is allowed.  
  Example: `True` / `False`

- **ACCOUNT_OWNERSHIP_ENABLED**  
  Whether new accounts can create or own workspaces by default. Admins can override per user.  
  Example: `True` / `False`

- **SOCIALACCOUNT_SIGNUP_ONLY**  
  If `True`, account sign-up is allowed only via third-party providers.  
  Example: `True` / `False`

- **SMTP_URL**  
  Connection string for sending emails.  
  Example: `smtp://127.0.0.1:1025`

- **DEFAULT_FROM_EMAIL**  
  Email address used for account management emails if SMTP is configured.  
  Example: `noreply@example.com`

- **STATIC_BUCKET_NAME**  
  The name of the AWS or GCP bucket used to serve static files if DEPLOYMENT_BACKEND is `aws` or `gcp`.  
  Example: `hydroserver-static-your-account-or-project-id`

- **MEDIA_BUCKET_NAME**  
  The name of the AWS or GCP bucket used to serve media files if DEPLOYMENT_BACKEND is `aws` or `gcp`.  
  Example: `hydroserver-media-your-account-or-project-id`

- **GS_PROJECT_ID**  
  The ID of your GCP project if DEPLOYMENT_BACKEND is `gcp`.  
  Example: `your-gcp-project-id`

Store sensitive environment variables (database credentials, API keys, etc.) securely, using a secret manager such as 
[AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html), 
[HashiCorp Vault](https://developer.hashicorp.com/vault), or [GCP Secret Manager](https://cloud.google.com/security/products/secret-manager).
Avoid committing secrets to version control or hardcoding them into configuration files.

### Serving Static and Media Files

Django is not optimized for serving static or media files in production. Recommended approaches include:

- Using a reverse proxy (e.g., [**NGINX**](https://nginx.org/)) to serve static and media volumes.  
- Offloading storage and delivery to a cloud service such as [**Amazon S3**](https://docs.aws.amazon.com/s3/) or 
  [**Google Cloud Storage**](https://cloud.google.com/storage/docs), optionally integrated with a 
  **Content Delivery Network (CDN)** service such as
  [**AWS CloudFront**](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html) or 
  [**Google Cloud CDN**](https://cloud.google.com/cdn/docs) for improved performance.  

Since these approaches bypass HydroServer’s internal authorization system, you may need to add additional security 
controls to protect private media files (for example, by using signed URLs).

### Email Configuration

HydroServer requires an SMTP server to send emails (e.g., password resets, email verification). For production, use a 
reliable external email provider such as [**Amazon Simple Email Service (SES)**](https://docs.aws.amazon.com/ses/) or 
[**Gmail SMTP**](https://developers.google.com/workspace/gmail/imap/imap-smtp) with authentication and TLS enabled.

### HTTPS

HydroServer should be served exclusively over HTTPS in production. Options include:
- Terminating TLS at a reverse proxy such as NGINX
- Using a managed certificate service (e.g., [**AWS Certificate Manager (ACM)**](https://docs.aws.amazon.com/acm/), 
  [**GCP Certificate Manager**](https://cloud.google.com/certificate-manager/docs/overview), 
  [**Let’s Encrypt**](https://letsencrypt.org/))

### Load Balancing and System Requirements

When planning a production deployment of HydroServer, it is important to consider performance, scalability, and fault 
tolerance. Key areas include:

- **Web Server Load Balancing**  
  For deployments that need to serve a large number of concurrent requests, place HydroServer behind a load balancer 
  (such as [**AWS Application Load Balancer (ALB)**](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html), 
  [**Google Cloud Load Balancer**](https://cloud.google.com/load-balancing), or [**NGINX**](https://nginx.org/)). 
  The load balancer distributes incoming traffic across multiple HydroServer containers or instances, improving 
  reliability and response times. When running HydroServer on serverless architecture, scaling HydroServer up and down 
  based on user traffic can also help lower costs.

- **Application Server Requirements**  
  HydroServer runs on the [**Django Framework**](https://www.djangoproject.com/), which by default uses a 
  single-threaded development server. In production, you should run HydroServer behind the built-in 
  [**Gunicorn**](https://gunicorn.org/) service with worker processes scaled to the available CPU and memory 
  resources. Containers or VMs should be sized to handle the expected workload, and additional replicas can be added 
  horizontally. Web server resource requirements will vary greatly depending on expected concurrent traffic and types 
  of workloads being performed with your HydroServer deployment.

- **Database Requirements**  
  PostgreSQL should be provisioned with sufficient CPU, memory, and disk throughput to handle both transactional 
  workload and background tasks (e.g., data ingestion). It is recommended to run PostgreSQL as a managed service where 
  available, or to configure regular backups and monitoring if self-managed.

- **Database Connection Pooling**  
  When scaling up the number of HydroServer web servers or worker processes, a large 
  number of short-lived database connections can be generated under high traffic loads. To avoid overwhelming 
  PostgreSQL with connection overhead for larger deployments, consider setting up a connection pooling service such as 
  [**PgBouncer**](https://www.pgbouncer.org/). Connection pooling reduces latency, stabilizes performance under high 
  concurrency, and allows more efficient use of database resources.

### Security and Access Control

When deploying HydroServer in production, you should implement multiple layers of security to reduce risk:

- **Database Access**  
  Restrict external access to the PostgreSQL database. It should only be accessible by the HydroServer service or other 
  explicitly authorized services (e.g., a database backup service). Consider using managed database services that 
  provide built-in encryption, automated backups, and fine-grained access control.

- **Network Restrictions**  
  Configure a firewall or security group to only allow required inbound traffic (typically HTTPS for HydroServer). 
  Deny all other external connections by default, and restrict outbound access to only the services HydroServer needs 
  to reach.

- **Secure Communication**  
  Ensure all internal services (e.g., HydroServer, reverse proxy, database) communicate over a secure network. For 
  distributed deployments, use TLS for connections between services where possible.

- **Authentication and Authorization**  
  Apply the principle of least privilege for all user roles and service accounts. For external APIs, consider rate 
  limiting and monitoring to detect unusual activity.

- **Regular Updates**  
  Keep HydroServer, its dependencies, and all supporting infrastructure (e.g., Docker base images, PostgreSQL) up to 
  date with the latest security patches.

- **Monitoring and Logging**  
  Enable logging at both the application and infrastructure layers. Use monitoring tools to detect suspicious activity, 
  unauthorized access attempts, and to track overall system health. HydroServer also provides a `/health-check` 
  endpoint that can be used by external monitoring services.

### HydroServer Management Commands

After provisioning your infrastructure, but before starting HydroServer’s web server, you must run several management 
commands to complete setup. In the demo deployments from the previous section, these steps are bundled into the 
convenience command:

```bash
python manage.py run_demo
```

This command is intended for demonstration purposes only. It runs the required setup steps and starts Django’s 
development server. Do **not** use it in production. For production deployments, run the following commands 
individually, or configure an automated process to run them once your database and storage volumes are ready:

```bash
python manage.py migrate
```  
Initializes all required HydroServer database tables in your PostgreSQL database.  
This must be run first. You may also need to rerun it when upgrading HydroServer (always check new version release 
notes first for details).

```bash
python manage.py collectstatic
```  
Copies HydroServer’s static files to the deployment location.  
Run this after upgrades to ensure new or updated static files are available.

```bash
python manage.py setup_admin_user
```
Creates the initial admin account for your HydroServer instance.  
Run once only. Additional admin accounts can be created later through the dashboard.

### Starting HydroServer with Gunicorn

HydroServer’s Docker image comes pre-installed with **Gunicorn** as the production-ready application server. After 
provisioning all deployment infrastructure, completing database migrations, collecting static files, and setting up an 
admin user, you can start the web server using Gunicorn.

Use the following entrypoint command when starting a HydroServer container in production:  

```bash
gunicorn hydroserver.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

- **hydroserver.wsgi:application**  
  Points Gunicorn to HydroServer's WSGI application.

- **--bind 0.0.0.0:8000**
  Exposes the application on all container network interfaces at port 8000. This will work for most deployment 
  methods, but it can be adjusted if needed.

- **--workers 3**
  The number of worker processes Gunicorn will spawn. Adjust this number based on available CPU cores and expected 
  traffic. Gunicorn generally recommends setting the number of workers to (2 * num_cores) + 1. The example above is
  intended for a HydroServer instance running on a single core.

After the server is running, visit your configured domain in a browser to access HydroServer.

## HydroServer Admin Dashboard

Once HydroServer is running and accessible, additional configuration settings can be managed through the admin 
dashboard.

1. **Access the Admin Dashboard**  
   Log in at: `https://<your-hydroserver-domain>/admin`

2. **Update the Default Site Domain**  
   - Go to **Sites** > **example.com**  
   - Change the default domain to match your HydroServer domain.  

3. **Configure Website Settings** (under **Web**)  
   - **Instance Configuration**: Customize the `About` page with information about your organization.  
   - **Analytics Configuration**: Optionally enable [Microsoft Clarity](https://clarity.microsoft.com/).  
   - **Map Configuration**: Define default map layers, view, geospatial, and elevation services.  
   - **Map Layers**: Add additional map layer options for pages that use maps.  
   - **Contact Information**: Add organization contact information for display on the `About` page.  

4. **Set Up Identity Providers**  
   - Navigate to **Social Applications** > **Add Social Application**.  
   - Select a supported provider (e.g., Google, HydroShare).  
   - Enter a unique ID, name, client ID/key, and secret key from the provider.  
   - (Optional) Add JSON settings, for example:  
     ```json
     {
       "allowSignUp": true,
       "allowConnection": true
     }
     ```  
     - **allowSignUp**: (true/false) — whether users can sign up and log in with this provider.  
     - **allowConnection**: (true/false) — whether users can connect the provider to an existing HydroServer account.  
   - Assign the default site that the provider can authenticate against.  

5. **Load Default Reference Data**  
   Populate the following models with data available to all users, or use the **Load Default Data** option in each
   model:  
   - Roles  
   - Observed Properties  
   - Processing Levels  
   - Result Qualifiers  
   - Sensors  
   - Units  

6. **Configure HydroShare Archival** (optional / experimental)  
   - First, configure HydroShare as a social application (see Step 4).  
   - Update the social application record with the following JSON:  
     ```json
     {
       "allowSignUp": false,
       "allowConnection": true
     }
     ```  
   - Navigate to **Orchestration Systems** > **Add Orchestration System**.  
     - Create a new record with:  
       - **Name**: `HydroShare Archival Manager`  
       - **Type**: `HydroShare`  
   - *Note: This archival configuration method is temporary and will be deprecated in a future release.*
