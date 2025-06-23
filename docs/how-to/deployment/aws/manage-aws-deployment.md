# Deploying HydroServer to Amazon Web Services

This guide walks you through setting up and maintaining a HydroServer deployment on AWS using Terraform and GitHub Actions. Before proceeding, we recommend reviewing [AWS security best practices](https://aws.amazon.com/security/) to ensure a secure deployment.

## Initial Setup

### Create an AWS Account and Configure IAM Roles and Policies

1. Create an [AWS account](https://aws.amazon.com/) if you don't already have one.
2. Follow [these instructions](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services) to configure GitHub's OpenID Connect (OIDC) for your AWS account. All workflows in the `hydroserver-ops` repository use this authentication method.
3. Create an IAM role to manage HydroServer deployments with Terraform. Configure a trust policy between AWS and **your** forked `hydroserver-ops` repository and user account or organization. Attach the following permissions policies:
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
     Or see the following [AWS IAM policy](https://github.com/hydroserver2/hydroserver/blob/main/docs/deployment/aws/aws-terraform-policy.json)
4. The policies above provide broad access for initial setup but can be restricted as needed.
5. Create an S3 bucket in your AWS account for Terraform to store its state. The bucket must have a globally unique name, default settings, and **must not** be publicly accessible. If you have multiple deployments in the same AWS account, they should share this Terraform bucket.
6. Use AWS Certificate Manager (ACM) to create or import a public certificate for the domain HydroServer will use.

### Set Up GitHub Environment

1. Fork the [hydroserver-ops](https://github.com/hydroserver2/hydroserver-ops) repository, which contains tools for managing HydroServer deployments.
2. In your forked repository, go to **Settings** > **Environments**.
3. Create a new environment with a simple alphanumeric name (e.g., `beta`, `prod`, `dev`). This name will be used for AWS services. All environment variables and secrets should be created in this environment.
4. Add the following GitHub **environment variables**:

   - **`AWS_ACCOUNT_ID`** – Your AWS account ID.
   - **`AWS_REGION`** – The AWS region for deployment (e.g., `us-east-1`).
   - **`AWS_IAM_ROLE`** – The IAM role name created in step 3.
   - **`AWS_ACM_CERTIFICATE_ARN`** – The ARN of the ACM certificate from step 6.
   - **`TERRAFORM_BUCKET`** – The S3 bucket name from step 5.
   - **`PROXY_BASE_URL`** – The domain name for HydroServer, including the protocol (e.g., `https://yourdomain.com`).
   - **`DEBUG`** _(Optional, default: `True`)_ – Set to `True` for non-production deployments.
   - **`ACCOUNT_SIGNUP_ENABLED`** _(Optional, default: `False`)_ – If `False`, admins must create user accounts.
   - **`ACCOUNT_OWNERSHIP_ENABLED`** _(Optional, default: `False`)_ – If `False`, users cannot create new workspaces.
   - **`SOCIALACCOUNT_SIGNUP_ONLY`** _(Optional, default: `False`)_ – If `True`, only third-party identity providers can be used for signup.
   - **`ENABLE_AUDITS`** _(Optional, default: `False`)_ – If `True`, HydroServer records database audit logs.

5. Add the following GitHub **environment secrets**:
   - **`DATABASE_URL`** _(Optional)_ – A PostgreSQL or Timescale Cloud database URL. If unset, Terraform provisions a new RDS database.  
     _Format:_ `postgresql://{user}:{password}@{host}:{port}/{database}`
   - **`SMTP_URL`** – Required for email notifications (account verification, password reset).  
     _Format:_ `smtps://{user}:{password}@{host}:{port}`
   - **`GOOGLE_MAPS_API_KEY`** – A Google Maps API key. [Set up Google Maps](https://developers.google.com/maps/documentation/embed/get-api-key).
   - **`GOOGLE_MAPS_MAP_ID`** _(Optional)_ – A Google Maps Map ID.

### Deploy AWS Services with Terraform

1. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** and select **HydroServer AWS Cloud Deployment**.
2. Run the workflow with:
   - The environment you created.
   - The **"Initialize HydroServer Deployment"** action.
   - (Optional) A specific HydroServer version if you don't want the latest.
3. The deployment process takes several minutes. Once complete:
   - Go to **AWS Console** > **CloudFront** > **Distributions** and note the generated CloudFront domain.
   - Create a DNS CNAME record pointing your HydroServer domain to the CloudFront domain.
   - Go to **AWS Console** > **Systems Manager** > **Parameter Store** to retrieve credentials for the auto-generated admin account.
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

## Updating HydroServer

To update your HydroServer deployment (new release, configuration changes):

1. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** > **HydroServer AWS Cloud Deployment**.
2. Run the workflow with:
   - The environment you created.
   - The **"Update HydroServer Deployment"** action for environment changes or new code deployments.
   - The **"Initialize HydroServer Deployment"** action for AWS service infrastructure updates.
   - (Optional) A specific HydroServer version.

## Tearing Down HydroServer

To delete your HydroServer deployment:

1. If Terraform provisioned an RDS database, manually delete it after making necessary backups.
2. Backup and empty the data-mgmt-app, media, and static S3 buckets associated with the HydroServer instance. **Do not empty the Terraform state bucket**. **Do not delete the buckets**.
3. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** > **HydroServer AWS Cloud Deployment**.
4. Run the workflow with:
   - The environment of the instance.
   - The **"Teardown HydroServer Deployment"** action.
