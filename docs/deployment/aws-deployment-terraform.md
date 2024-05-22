# Deploying HydroServer to AWS and Timescale Cloud

This guide will walk you through how to set up and maintain a HydroServer deployment on AWS and Timescale Cloud services using Terraform and GitHub Actions. We recommend you familiarize yourself with AWS security best practices before setting up HydroServer in AWS.

## Fork the hydroserver-ops Repository
1. Create a fork of the [hydroserver-ops](https://github.com/hydroserver2/hydroserver-ops) repository, which contains tools you'll use for managing your HydroServer deployments. You'll need to enable workflows on your forked repository before you can run them.
2. Go to your forked repository settings and navigate to "Environments".
3. Create a new environment with a simple name unique to your account (e.g., beta, prod, dev), which you will use in subsequent steps. This new environment name will be used to identify various AWS and Timescale Cloud services. All environment variables and secrets mentioned in this guide should be created under this environment.

## Create an AWS Account and Configure IAM Roles and Policies
1. Create an [AWS](https://aws.amazon.com/) account if you don't already have one.
2. Follow [these instructions](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services) to configure GitHub's OpenID Connect (OIDC) for your AWS account. All workflows in the github-ops repository are set up to use this authentication method.
3. Create an IAM role for managing HydroServer deployments with Terraform. You will need to follow the instructions in the previous step to configure a trust policy between AWS and ***your*** forked hydroserver-ops repository and user account or organization. Grant it the following permissions policies:
   - AmazonS3FullAccess
   - AWSWAFFullAccess,
   - CloudFrontFullAccess
   - AdministratorAccess-AWSElasticBeanstalk.
4. You also need to create and apply [this policy](https://github.com/hydroserver2/hydroserver-ops/blob/main/terraform/aws/terraform-iam-policy.json) to the IAM role for limited IAM management permissions. Replace all instances of YOUR_ACCOUNT_ID with your own AWS account ID.
5. The IAM policy in the previous step references [this permission boundary policy](https://github.com/hydroserver2/hydroserver-ops/blob/main/terraform/aws/iam-ec2-permissions-boundary.json). Create the policy and name it "HydroServerIAMPermissionBoundary". If you need to modify any of these policies, take care to avoid gaps that could lead to privilege escalation vulnerabilities.
6. Create an S3 bucket in your AWS account for Terraform to use to manage your deployments and store sensitive credentials you'll need to access later. Give it a globally unique name, use the default settings, and make sure it is not publicly accessible. You only need one of these buckets per AWS account; if you have multiple deployments on the same AWS account, they should use the same Terraform bucket.
7. Create the following GitHub environment variables:
   - AWS_ACCOUNT_ID: Your AWS account ID.
   - AWS_REGION: The AWS region you want to deploy your service to (e.g. us-east-1).
   - AWS_IAM_ROLE: The name of the IAM role you created in step 3.
   - TERRAFORM_BUCKET: The name of the S3 bucket you created in step 6.

## Set Up Timescale Cloud Account
1. Create a [Timescale Cloud](https://www.timescale.com/) account and project. Take note of your project ID.
2. Under project settings, create a set of client credentials for your project. These client credentials are only needed during the initial setup described in this guide. After you finish setting up HydroServer, you may want to disable these credentials.
3. Create the following GitHub environment variable:
   - TIMESCALE_PROJECT_ID: The project ID from step 1.
4. Create the following GitHub environment secrets:
   - TIMESCALE_ACCESS_KEY: The access key for the credentials you created in step 2.
   - TIMESCALE_SECRET_KEY: The secret key for the credentials you created in step 2.

## Terraform Setup for AWS Services
1. From your hydroserver-ops repository, go to Actions > Workflows and click "Create HydroServer AWS Cloud Deployment".
2. Run the workflow and input the same environment name used for your GitHub environment.
3. The workflow will take several minutes to complete. Once complete, you should have an Elastic Beanstalk app and environment, a Cloudfront distribution, and several S3 buckets associated with your environment. At this point, these services will not have any HydroServer code deployed to them, but you can check the AWS Console to verify that they are running.

## Additional Environment Configuration
1. Using a Google account, follow the instructions [here](https://developers.google.com/maps/documentation/embed/get-api-key) to generate a Google Maps API key and map ID for your HydroServer environment.
2. Create the following GitHub environment variables:
   - DEBUG: Set to 'True' for development deployments or 'False' for production deployments.
   - CLOUDFRONT_ID: You can retrieve the CloudFront distribution ID from the AWS CloudFront dashboard.
   - ALLOWED_HOSTS: Enter your CloudFront domain name. This variable accepts a comma-separated list of domains Django will accept requests from, so you can also enter the autogenerated Elastic Beanstalk domain for testing. If you're attaching a custom domain to your CloudFront distribution, you should enter that domain. For security reasons, you should limit ALLOWED_HOSTS to only domains you intend users or developers to be able to access HydroServer from.
   - PROXY_BASE_URL: Enter the CloudFront domain name, including the protocol (e.g. https://). If you're using a custom domain instead of the CloudFront generated domain, use that base URL instead. Some pages and resources, such as the admin dashboard, will only work when accessed through this base URL.
3. Create the following GitHub environment secrets:
   - DJANGO_SECRET_KEY: Generate and store a Django secret key here.
   - GOOGLE_MAPS_API_KEY: Enter the Google Maps API key you created in step 1.
   - GOOGLE_MAPS_MAP_ID: Enter the Google Maps map ID you created in step 1.
   
## Timescale Cloud Database Setup
1. From your hydroserver-ops repo, click Actions > Workflows and select "Create HydroServer Timescale Cloud Database".
2. Run the workflow, providing your environment name, Django admin account credentials, partition interval (default: 365 days), and optional HydroServer version.
   - The Django credentials you provide will be used to create a superuser you can use to log in to the Django admin dashboard. You can change these later if you wish.
   - The partition interval is used to chunk the HydroServer observations table. Depending on your use cases, you may want to adjust this value. You can read more about Timescale hypertables and partitioning [here](https://docs.timescale.com/use-timescale/latest/hypertables/about-hypertables/). Although Timescale Cloud uses a default partition interval of 7 days, the default used by the hydroserver-ops repo is 365 days.
   - You can optionally specify a HydroServer version to base the database configuration on. If you want to use the latest version of HydroServer, leave this field blank.
3. After the workflow completes, you should see a new service on your Timescale Cloud dashboard. To connect to this service, retrieve the Timescale database connection details from the output folder in the Terraform S3 bucket you created earlier.
4. Create the following GitHub environment secret:
   - DATABASE_URL: Use the database connection string from the Timescale connection details file you looked up in step 3.
  
## Email Settings
1. To enable email services for HydroServer (used for account verification and password reset), first set up an SMTP server using a service such as [Amazon SES](https://docs.aws.amazon.com/ses/latest/dg/send-email-smtp.html).
2. Create the following GitHub environment variables:
   - EMAIL_HOST: The host for your SMTP service.
   - EMAIL_PORT: The port for your SMTP service.
3. Create the following GitHub environment secrets:
   - EMAIL_HOST_USER: The username associated with your SMTP service.
   - EMAIL_HOST_PASSWORD: The password associated with your SMTP service.

## Google OAuth Settings
1. To enable Google OAuth for HydroServer account creation, follow the instructions [here](https://developers.google.com/identity/protocols/oauth2) to create client credentials for HydroServer.
2. Use the following pattern for the Google OAuth authorized redirect URL: {PROXY_BASE_URL}/api/account/google/auth
3. Create the following GitHub environment secrets:
   - OAUTH_GOOGLE_CLIENT: The Google OAuth client key for the credentials you just created.
   - OAUTH_GOOGLE_SECRET: The Google OAuth secret key for the credentials you just created.

## ORCID OAuth Settings
1. To enable ORCID OAuth for HydroServer account creation, follow the instructions [here](https://info.orcid.org/documentation/api-tutorials/api-tutorial-get-and-authenticated-orcid-id/) to create client credentials for HydroServer.
2. Use the following pattern for the ORCID OAuth authorized redirect URL: {PROXY_BASE_URL}/api/account/orcid/auth
3. Create the following GitHub environment secrets:
   - OAUTH_ORCID_CLIENT: The ORCID OAuth client key for the credentials you just created.
   - OAUTH_ORCID_SECRET: The ORCID OAuth secret key for the credentials you just created.

## HydoShare OAuth Settings
1. To enable HydroShare OAuth for HydroServer data archival, create a HydroShare account and use [this page](https://www.hydroshare.org/o/applications/) to create client credentials for HydroServer.
2. Use the following pattern for the HydroShare OAuth authorized redirect URL: {PROXY_BASE_URL}/api/account/hydroshare/auth
3. Create the following GitHub environment secrets:
   - OAUTH_HYDROSHARE_CLIENT: The HydroShare OAuth client key for the credentials you just created.
   - OAUTH_HYDROSHARE_SECRET: The HydroShare OAuth secret key for the credentials you just created.

## Deploy HydroServer to AWS Cloud
1. From the hydroserver-ops repo, click Actions > Workflows and choose "Deploy HydroServer to AWS Cloud Deployment".
2. Run the workflow, entering your GitHub environment name and optional HydroServer version (leave blank to use the latest version).
3. After the workflow completes, your HydroServer instance should be running at the autogenerated CloudFront URL. You can log in to the admin dashboard at /admin/ using the admin credentials you entered during the Timescale Cloud setup workflow.

## Updating HydroServer
1. If you want to update HydroServer, just rerun the workflow from the previous section.
2. This workflow handles code updates and database migrations, but you should check the release notes for the version you're updating to in case there are any additional steps required for that version.
3. Updated environment variables and secrets in GitHub will not be automatically applied to your deployment until you run this workflow. If you are redeploying a version of HydroServer you've already deployed, you will need to first delete that application version from Elastic Beanstalk or the deployment will fail. Most of these settings can also be modified through the Elastic Beanstalk dashboard configuration settings if you want to change any settings without redeploying through GitHub.

## Set Up a Custom HydroServer Domain
1. If you want to host HydroServer behind a custom domain, you can do so using [Route 53](https://aws.amazon.com/route53/) or another DNS provider.
2. Follow the instructions [here](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/CNAMEs.html) to host CloudFront behind your custom domain.
3. Remember to update your environment's PROXY_BASE_URL and ALLOWED_HOST settings accordingly.
