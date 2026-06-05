# Setting Up a Production Deployment

This guide provides an overview for deploying HydroServer in a production environment. It is intended to help system 
administrators and developers get started with setting up key infrastructure needed to run HydroServer reliably and at
scale based on their needs and use-cases. The guide includes an overview of required infrastructure and production
configuration settings.

## HydroServer Required Infrastructure 

Each HydroServer release includes a [**container image**](https://github.com/hydroserver2/hydroserver/pkgs/container/hydroserver) 
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

### Enabling Celery for HydroServer

HydroServer optionally supports Celery for scheduling background tasks. To run Celery, you must set up several 
additional services, including at least one worker instance, a scheduler, and a broker such as
[Redis](https://redis.io/docs/latest/).

The following HydroServer settings can be used to configure Celery:

- **CELERY_ENABLED**  
  Controls whether Celery scheduling is enabled. If not enabled, all data processing will be handled by HydroServer's
  web server.
  Example: `True` / `False`

- **CELERY_BROKER_URL** 
  The URL of the broker service Celery should use to orchestrate tasks.
  Example: `redis://127.0.0.1:6379/0`

To start a Celery worker, use the following entrypoint command with HydroServer’s Docker image. This container must
have database and broker access.

```bash
celery -A hydroserver worker --loglevel=INFO
```

To start a Celery scheduler, use the following entrypoint command with HydroServer’s Docker image. This container must
have database and broker access.

```bash
celery -A hydroserver beat --loglevel=INFO
```

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

### Updating to a New Version

To update an existing HydroServer deployment to a new version:

1. **Read the release notes** for every version between your current version and the target version. Some releases include required manual steps, database migration prerequisites, or breaking changes that must be addressed before or after upgrading. Release notes are published on the [HydroServer GitHub releases page](https://github.com/hydroserver2/hydroserver/releases).

2. **Back up your database.** Always take a snapshot of your PostgreSQL database before applying an upgrade, especially for releases that include database migrations.

3. **Pull the new image.** Update your deployment configuration to reference the new container image version and redeploy.

4. **Run post-deployment management commands.** After the new container is running, execute the following:

   ```bash
   python manage.py collectstatic
   ```
   Collects any new or updated static files included in the release.

   ```bash
   python manage.py migrate
   ```
   Applies any database schema changes included in the release.

5. **Restart Celery workers** (if applicable). If your deployment uses Celery for background task scheduling, restart your worker and beat containers after the upgrade to pick up any changes.
