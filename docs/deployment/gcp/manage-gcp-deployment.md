# Deploying HydroServer to Google Cloud Services

This guide walks you through setting up and maintaining a HydroServer deployment on GCP using Terraform and GitHub Actions.

## Initial Setup

### Create a GCP Account and Configure IAM Roles and Policies

1. Create a [GCP account](https://cloud.google.com/) if you don't already have one.
2. Follow [these instructions](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-google-cloud-platform) to configure GitHub's OpenID Connect (OIDC) for your GCP account. All workflows in the `hydroserver-ops` repository use this authentication method.
3. Create an IAM role to manage HydroServer deployments with Terraform. Configure a trust policy between GCP and **your** forked `hydroserver-ops` repository and user account or organization. Attach the following permissions policies:
   - `CloudFrontFullAccess`
   - `AWSWAFFullAccess`
   - `AWSAppRunnerFullAccess`
   - `AmazonS3FullAccess`
   - `IAMFullAccess`
   - `AmazonRDSFullAccess`
   - `AmazonEC2FullAccess`
   - `AmazonElasticContainerRegistryPublicFullAccess`
   - `AWSKeyManagementServicePowerUser`
   - `AWSKeyManagementService`
     - `Encrypt`, `Decrypt`, `GenerateDataKey`
   - `AmazonSSMFullAccess`
4. The policies above provide broad access for initial setup but can be restricted as needed.
5. Create a Cloud Storage bucket in your GCP project for Terraform to store its state. The bucket must have a globally unique name, default settings, and **must not** be publicly accessible. If you have multiple deployments in the same GCP project, they should share this Terraform bucket.
6. Use GCP Certificate Manager to create or upload a public classic certificate for the domain HydroServer will use.

### Set Up GitHub Environment

1. Fork the [hydroserver-ops](https://github.com/hydroserver2/hydroserver-ops) repository, which contains tools for managing HydroServer deployments.
2. In your forked repository, go to **Settings** > **Environments**.
3. Create a new environment with a simple alphanumeric name (e.g., `beta`, `prod`, `dev`). This name will be used for GCP services. All environment variables and secrets should be created in this environment.
4. Add the following GitHub **environment variables**:
   - **`GCP_PROJECT_ID`** – Your GCP project ID.
   - **`GCP_REGION`** – The GCP region for deployment (e.g., `us-west3`).
   - **`GCP_IDENTITY_PROVIDER`** – The GitHub OIDC provider you created in step 2 of `Create a GCP Account and Configure IAM Roles and Policies` (e.g., `projects/your-project-id/locations/global/workloadIdentityPools/your-workload-identity-pool-id/providers/your-workload-identity-provider-id`).
   - **`GCP_SERVICE_ACCOUNT`** – The email of the service account you created in step 2 of `Create a GCP Account and Configure IAM Roles and Policies`.
   - **`GCP_SSL_CERTIFICATE_NAME`** – The name of the classic certificate from step 6 of `Create a GCP Account and Configure IAM Roles and Policies`.
   - **`TERRAFORM_BUCKET`** – The Cloud Storage bucket name from step 5.
   - **`PROXY_BASE_URL`** – The domain name for HydroServer, including the protocol (e.g., `https://yourdomain.com`).
   - **`DEBUG`** *(Optional, default: `True`)* – Set to `True` for non-production deployments.
   - **`ACCOUNT_SIGNUP_ENABLED`** *(Optional, default: `False`)* – If `False`, admins must create user accounts.
   - **`ACCOUNT_OWNERSHIP_ENABLED`** *(Optional, default: `False`)* – If `False`, users cannot create new workspaces.
   - **`SOCIALACCOUNT_SIGNUP_ONLY`** *(Optional, default: `False`)* – If `True`, only third-party identity providers can be used for signup.
   - **`ENABLE_AUDITS`** *(Optional, default: `False`)* – If `True`, HydroServer records database audit logs.

5. Add the following GitHub **environment secrets**:
   - **`DATABASE_URL`** *(Optional)* – A PostgreSQL or Timescale Cloud database URL. If unset, Terraform provisions a new Cloud SQL database.  
     *Format:* `postgresql://{user}:{password}@{host}:{port}/{database}`
   - **`SMTP_URL`** – Required for email notifications (account verification, password reset).  
     *Format:* `smtps://{user}:{password}@{host}:{port}`
   - **`GOOGLE_MAPS_API_KEY`** – A Google Maps API key. [Set up Google Maps](https://developers.google.com/maps/documentation/embed/get-api-key).
   - **`GOOGLE_MAPS_MAP_ID`** *(Optional)* – A Google Maps Map ID.

### Deploy GCP Services with Terraform

1. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** and select **HydroServer GCP Cloud Deployment**.
2. Run the workflow with:
   - The environment you created.
   - The **"Initialize HydroServer Deployment"** action.
   - (Optional) A specific HydroServer version if you don't want the latest.
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
4. Populate the following models with default data you want available to all users:
   - Roles
   - Observed Properties
   - Processing Levels
   - Result Qualifiers
   - Sensors
   - Units

## Updating HydroServer

To update your HydroServer deployment (new release, configuration changes):

1. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** > **HydroServer GCP Cloud Deployment**.
2. Run the workflow with:
   - The environment you created.
   - The **"Update HydroServer Deployment"** action for environment changes or new code deployments.
   - The **"Initialize HydroServer Deployment"** action for GCP service infrastructure updates.
   - (Optional) A specific HydroServer version.

## Tearing Down HydroServer

To delete your HydroServer deployment:

1. If Terraform provisioned a Cloud SQL database, manually delete it after making necessary backups.
2. Backup and empty the data-mgmt-app, media, and static Cloud Storage buckets associated with the HydroServer instance. **Do not empty the Terraform state bucket**. **Do not delete the buckets**.
3. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** > **HydroServer GCP Cloud Deployment**.
4. Run the workflow with:
   - The environment of the instance.
   - The **"Teardown HydroServer Deployment"** action.