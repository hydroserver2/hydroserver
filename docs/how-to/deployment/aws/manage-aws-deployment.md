# Deploying HydroServer to Amazon Web Services

This guide provides instructions for setting up and maintaining a HydroServer deployment on AWS using Terraform and GitHub Actions. Before proceeding, we recommend reviewing [AWS security best practices](https://aws.amazon.com/security/) to ensure a secure deployment.

## Amazon Web Services

The HydroServer deployment in this guide will use the following AWS services. Detailed Terraform service configurations can be found in [hydroserver-ops](https://github.com/hydroserver2/hydroserver-ops/tree/main/terraform/aws). Default compute, memory, and storage resources are set to minimum values by default and can be adjusted as needed after deployment using the Amazon Web Services Console. Use [Amazon Web Service's pricing calculator](https://calculator.aws) to generate cost estimates for your deployment.
- **[App Runner](https://docs.aws.amazon.com/apprunner/latest/dg)**: HydroServer's API will be deployed to AWS App Runner. The default configuration is one instance with 1 vCPU and 2 GB Memory.
- **[CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide)**: HydroServer web services will be served through CloudFront.
- **[Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide)**: A basic VPC will be set up to manage internal HydroServer networking.
- **[Elastic Container Registry](https://docs.aws.amazon.com/AmazonECR/latest/userguide)**: HydroServer's Django image will be copied to AWS Elastic Container Registry for App Runner to deploy with.
- **[Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide) (Optional)**: If not connecting to an external database, HydroServer's PostgreSQL database will be deployed using Amazon's Relational Database Service. The default machine type is `db.t4g.micro` (2 vCPU, 1 GB Memory).
- **[IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide)**: IAM service accounts will be set up to run HydroServer services.
- **[Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide)**: Static, media, and web app files will be stored and served from AWS S3 Buckets. Terraform will store the Airflow deployment state in an AWS S3 Bucket.

## Initial Setup

### Set Up GitHub Environment
1. Fork the [hydroserver-ops](https://github.com/hydroserver2/hydroserver-ops) repository, which contains tools for managing HydroServer deployments.
2. In your forked repository, go to **Settings** > **Environments**.
3. Create a new environment with a simple alphanumeric name (e.g., `beta`, `prod`, `dev`). This name will be used for AWS services. All environment variables and secrets should be created in this environment.

### Create an AWS Account and Configure IAM Roles and Policies

1. Create an [AWS account](https://aws.amazon.com/) if you don't already have one.
2. Follow [these instructions](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services) to configure GitHub's OpenID Connect (OIDC) for your AWS account. All workflows in the `hydroserver-ops` repository use this authentication method.
3. Create an IAM role to manage HydroServer deployments with Terraform. Configure a trust policy between AWS and **your** forked `hydroserver-ops` repository and user account or organization.
4. Attach these [IAM permissions](https://github.com/hydroserver2/hydroserver/blob/main/docs/how-to/deployment/aws/aws-terraform-policy.json) to the role.
5. Create an S3 bucket in your AWS account for Terraform to store its state. The bucket must have a globally unique name, default settings, and **must not** be publicly accessible. If you have multiple deployments in the same AWS account, they should share this Terraform bucket.
6. Use AWS Certificate Manager (ACM) to create or import a public certificate for the domain HydroServer will use.

### Define Environment Variables

1. In your `hydroserver-ops` repository, go to **Settings** > **Environments**.
2. Add the following GitHub **environment variables**:
   - **`AWS_ACCOUNT_ID`** – Your AWS account ID.
   - **`AWS_REGION`** – The AWS region for deployment (e.g., `us-east-1`).
   - **`AWS_IAM_ROLE`** – The IAM role name created in step 3 of `Create an AWS Account and Configure IAM Roles and Policies`.
   - **`AWS_ACM_CERTIFICATE_ARN`** – The ARN of the ACM certificate from step 6 of `Create an AWS Account and Configure IAM Roles and Policies`.
   - **`TERRAFORM_BUCKET`** – The S3 bucket name from step 5 of `Create an AWS Account and Configure IAM Roles and Policies`.
   - **`PROXY_BASE_URL`** – The domain name for HydroServer, including the protocol (e.g., `https://yourdomain.com`).
   - **`DEBUG`** _(Optional, default: `True`)_ – Set to `True` for non-production deployments.
   - **`ACCOUNT_SIGNUP_ENABLED`** _(Optional, default: `False`)_ – If `False`, admins must create user accounts.
   - **`ACCOUNT_OWNERSHIP_ENABLED`** _(Optional, default: `False`)_ – If `False`, users cannot create new workspaces.
   - **`SOCIALACCOUNT_SIGNUP_ONLY`** _(Optional, default: `False`)_ – If `True`, only third-party identity providers can be used for signup.
   - **`ENABLE_AUDITS`** _(Optional, default: `False`)_ – If `True`, HydroServer records database audit logs.
3. Add the following GitHub **environment secrets**:
   - **`DATABASE_URL`** _(Optional)_ – A PostgreSQL database URL. If unset, Terraform provisions a new RDS database.  
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
   - _(Optional)_ A specific HydroServer version if you don't want the latest.
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

### Connect to HydroServer's Database (Optional)

If you need to connect to the HydroServer database, you can do so using AWS Systems Manager (SSM) port forwarding. This method avoids exposing your database to the public internet.

1. Install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide) if you haven't already done so.
2. Configure the CLI and log in to your AWS account using your IAM user credentials:
   ```bash
   aws configure
   ```
3. Install the [Session Manager Plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html).
4. From the AWS Console or CLI, find and note the following for the next steps:
   - **EC2** > **Instances** > **hydroserver-your-env-ssm-bastion** > **Instance ID**
   - **RDS** > **Databases** > **hydroserver-your-env** > **Endpoint**
   - **Parameter Store** > **/hydroserver-your-env-api/database-url** > **Value**
5. Start a port forwarding session to the RDS instance via the EC2 bastion host:
   ```bash
   aws ssm start-session \
     --target i-your-bastion-instance-id \
     --document-name AWS-StartPortForwardingSessionToRemoteHost \
     --parameters '{"host":["your-db-endpoint.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["5432"]}'
   ```
6. Using the credentials in the database connection URL, you can now connect to HydroServer's database using your preferred database client.

## Updating HydroServer

To update your HydroServer deployment (new release, configuration changes):

1. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** > **HydroServer AWS Cloud Deployment**.
2. Run the workflow with:
   - The environment you created.
   - The **"Update HydroServer Deployment"** action for environment changes or new code deployments.
   - The **"Initialize HydroServer Deployment"** action for AWS service infrastructure updates.
   - _(Optional)_ A specific HydroServer version.

## Tearing Down HydroServer

To delete your HydroServer deployment:

1. If Terraform provisioned an RDS database, manually delete it after making necessary backups.
2. Backup and empty the data-mgmt-app, media, and static S3 buckets associated with the HydroServer instance. **Do not empty the Terraform state bucket**. **Do not delete the buckets**.
3. In your `hydroserver-ops` repository, go to **Actions** > **Workflows** > **HydroServer AWS Cloud Deployment**.
4. Run the workflow with:
   - The environment of the instance.
   - The **"Teardown HydroServer Deployment"** action.
