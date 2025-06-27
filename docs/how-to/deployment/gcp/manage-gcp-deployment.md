# Deploying HydroServer to Google Cloud Platform

This guide provides instructions for setting up and maintaining a HydroServer deployment on GCP using Terraform and GitHub Actions. Before proceeding, we recommend reviewing [GCP security best practices](https://cloud.google.com/security/best-practices) to ensure a secure deployment.

## Google Cloud Platform

The HydroServer deployment in this guide will use the following GCP services. Detailed Terraform service configurations can be found in [hydroserver-ops](https://github.com/hydroserver2/hydroserver-ops/tree/main/terraform/gcp). Default compute, memory, and storage resources are set to minimum values by default and can be adjusted as needed after deployment using the Google Cloud Console. Use [Google Cloud's pricing calculator](https://cloud.google.com/products/calculator) to generate cost estimates for your deployment.
- **[Cloud Run](https://cloud.google.com/run/docs)**: HydroServer's API will be deployed to GCP Cloud Run. The default configuration is one instance with 1 vCPU and 2 GB Memory.
- **[Network Services](https://cloud.google.com/docs/networking)**: HydroServer web services will be served through Cloud CDN and Load Balancer.
- **[Cloud Armor](https://cloud.google.com/armor/docs)**: A basic web application firewall will be set up using GCP Cloud Armor.
- **[Artifact Registry](https://cloud.google.com/artifact-registry/docs)**: HydroServer's Django image will be copied to GCP Artifact Registry for Cloud Run to deploy with.
- **[Cloud SQL](https://cloud.google.com/sql/docshttps://cloud.google.com/sql/docs) _(Optional)_**: If not connecting to an external database, HydroServer's PostgreSQL database will be deployed using Cloud SQL. The default machine type is `db-f1-micro` (1 vCPU, 0.614 GB Memory).
- **[IAM](https://cloud.google.com/iam/docs)**: IAM service accounts will be set up to run HydroServer services.
- **[Cloud Storage](https://cloud.google.com/storage/docs)**: Static, media, and web app files will be stored and served from GCP Cloud Storage Buckets. Terraform will store the Airflow deployment state in a GCP Cloud Storage Bucket.

## Initial Setup

### Set Up GitHub Environment
1. Fork the [hydroserver-ops](https://github.com/hydroserver2/hydroserver-ops) repository, which contains tools for managing HydroServer deployments.
2. In your forked repository, go to **Settings** > **Environments**.
3. Create a new environment with a simple alphanumeric name (e.g., `beta`, `prod`, `dev`). This name will be used for GCP services. All environment variables and secrets should be created in this environment.

### Create a GCP Account and Configure IAM Roles and Policies

1. Create a [GCP account](https://cloud.google.com/) if you don't already have one.
2. Follow [these instructions](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-google-cloud-platform) to configure GitHub's OpenID Connect (OIDC) for your GCP account. All workflows in the `hydroserver-ops` repository use this authentication method.
3. Create an IAM role to manage HydroServer deployments with Terraform. Configure a trust policy between GCP and **your** forked `hydroserver-ops` repository and user account or organization. 
4. Attach these [IAM permissions](https://github.com/hydroserver2/hydroserver/blob/main/docs/how-to/deployment/gcp/gcp-terraform-permissions.md) to the role.
5. Create a Cloud Storage bucket in your GCP project for Terraform to store its state. The bucket must have a globally unique name, default settings, and **must not** be publicly accessible. If you have multiple deployments in the same GCP project, they should share this Terraform bucket.
6. Use GCP Certificate Manager to create or upload a public classic certificate for the domain HydroServer will use.
7. Ensure the following Google APIs are enabled for your project:
   - Compute Engine API
   - Artifact Registry API
   - Secret Manager API
   - Cloud SQL Admin API
   - Cloud Run Admin API

### Define Environment Variables

1. In your `hydroserver-ops` repository, go to **Settings** > **Environments**.
2. Add the following GitHub **environment variables**:
   - **`GCP_PROJECT_ID`** – Your GCP project ID.
   - **`GCP_REGION`** – The GCP region for deployment (e.g., `us-west3`).
   - **`GCP_IDENTITY_PROVIDER`** – The GitHub OIDC provider you created in step 2 of `Create a GCP Account and Configure IAM Roles and Policies` (e.g., `projects/your-project-id/locations/global/workloadIdentityPools/your-workload-identity-pool-id/providers/your-workload-identity-provider-id`).
   - **`GCP_SERVICE_ACCOUNT`** – The email of the service account you created in step 2 of `Create a GCP Account and Configure IAM Roles and Policies`.
   - **`GCP_SSL_CERTIFICATE_NAME`** – The name of the classic certificate from step 6 of `Create a GCP Account and Configure IAM Roles and Policies`.
   - **`TERRAFORM_BUCKET`** – The Cloud Storage bucket name from step 5 of `Create a GCP Account and Configure IAM Roles and Policies`.
   - **`PROXY_BASE_URL`** – The domain name for HydroServer, including the protocol (e.g., `https://yourdomain.com`).
   - **`DEBUG`** _(Optional, default: `True`)_ – Set to `True` for non-production deployments.
   - **`ACCOUNT_SIGNUP_ENABLED`** _(Optional, default: `False`)_ – If `False`, admins must create user accounts.
   - **`ACCOUNT_OWNERSHIP_ENABLED`** _(Optional, default: `False`)_ – If `False`, users cannot create new workspaces.
   - **`SOCIALACCOUNT_SIGNUP_ONLY`** _(Optional, default: `False`)_ – If `True`, only third-party identity providers can be used for signup.
   - **`ENABLE_AUDITS`** _(Optional, default: `False`)_ – If `True`, HydroServer records database audit logs.
3. Add the following GitHub **environment secrets**:
   - **`DATABASE_URL`** _(Optional)_ – A PostgreSQL or Timescale Cloud database URL. If unset, Terraform provisions a new Cloud SQL database.  
     *Format:* `postgresql://{user}:{password}@{host}:{port}/{database}`
   - **`SMTP_URL`** – Required for email notifications (account verification, password reset).  
     *Format:* `smtps://{user}:{password}@{host}:{port}`
   - **`GOOGLE_MAPS_API_KEY`** – A Google Maps API key. [Set up Google Maps](https://developers.google.com/maps/documentation/embed/get-api-key).
   - **`GOOGLE_MAPS_MAP_ID`** _(Optional)_ – A Google Maps Map ID.

### Deploy GCP Services with Terraform

1. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** and select **HydroServer GCP Cloud Deployment**.
2. Run the workflow with:
   - The environment you created.
   - The **"Initialize HydroServer Deployment"** action.
   - _(Optional)_ A specific HydroServer version if you don't want the latest.
3. The deployment process takes several minutes. Once complete:
   - Go to **GCP Console** > **Network Services** > **Load Balancing** > **Frontends** and note the IP address of HydroServer's load balancer frontend.
   - Create a DNS A record pointing your HydroServer domain to the GCP load balancer IP address.
   - Go to **GCP Console** > **Security** > **Secret Manager** to retrieve credentials for the auto-generated admin account (default-admin-email and default-admin-password).
4. Verify HydroServer is running by visiting your configured domain in a browser.  
   - The admin dashboard is available at `https://yourdomain.com/admin/`.

### Configure HydroServer

1. Log in to the HydroServer admin dashboard.
2. Go to **Sites** > **example.com** and update the default domain to match your HydroServer domain.
3. Navigate to **Social Applications** > **Add Social Application** to register identity providers (e.g., Google, HydroShare).
4. Populate the following models with default data you want available to all users, or load the preset defaults by clicking **Load Default Data** for each model:
   - Roles
   - Observed Properties
   - Processing Levels
   - Result Qualifiers
   - Sensors
   - Units
5. To configure HydroShare archival, do the following:
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
    
### Connect to HydroServer's Database (Optional)

If you need to connect to the HydroServer database, you can do so using [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/connect-instance-auth-proxy). This method avoids exposing your database to the public internet.

1. Install the [gcloud CLI](https://cloud.google.com/sdk/docs/install) if you haven't already done so.
2. Initialize the CLI by logging in to your Google account and selecting the project you where you deployed HydroServer:
   ```bash
   gcloud init
   ```
3. Install [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/connect-instance-auth-proxy#install-proxy)
4. Start Cloud SQL Auth Proxy:
   ```bash
   cloud-sql-proxy your-hydroserver-project:your-hydroserver-region:your-hydroserver-instance --port=5432
   ```
5. Using the gcloud CLI or GCP Console, retrieve the database connection URL from the GCP Secret Manager.
6. Using the credentials in the database connection URL, you can now connect to HydroServer's database using your preferred database client.

## Updating HydroServer

To update your HydroServer deployment (new release, configuration changes):

1. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** > **HydroServer GCP Cloud Deployment**.
2. Run the workflow with:
   - The environment you created.
   - The **"Update HydroServer Deployment"** action for environment changes or new code deployments.
   - The **"Initialize HydroServer Deployment"** action for GCP service infrastructure updates.
   - _(Optional)_ A specific HydroServer version.

## Tearing Down HydroServer

To delete your HydroServer deployment:

1. If Terraform provisioned a Cloud SQL database, manually delete it after making necessary backups.
2. Backup and empty the data-mgmt-app, media, and static Cloud Storage buckets associated with the HydroServer instance. **Do not empty the Terraform state bucket**. **Do not delete the buckets**.
3. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** > **HydroServer GCP Cloud Deployment**.
4. Run the workflow with:
   - The environment of the instance.
   - The **"Teardown HydroServer Deployment"** action.
