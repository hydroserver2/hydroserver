# HydroServer AWS Deployment

This guide provides step-by-step instructions for setting up a HydroServer deployment on AWS.

## AWS Required Services

Before proceeding with this guide, ensure that you have an active AWS account and a basic understanding of cloud security concepts. It is recommended to appropriately scope any roles and policies used for setting up and managing the services.

The HydroServer AWS deployment outlined in this guide uses the following AWS services:

- CloudFront
- Elastic Beanstalk
- EC2 (Load Balancers)
- Amazon S3
- Amazon SES

Additionally, the guide covers the setup of an AWS managed domain for HydroServer, using the following services:

- Route 53
- AWS Certificate Manager (ACM)

## AWS Domain Registration and Certificate Requests

If you already have a domain and SSL certificate, you can skip to the next section for instructions on importing your SSL certificate into AWS. For a more detailed walkthrough on domain registration and certificate requests, refer to the following pages:

- [Registering a new domain](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html)
- [Requesting a public certificate](https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html)

### Register a Domain

To set up an AWS managed domain, log in to the AWS Console and navigate to the Route 53 service dashboard. Under "Register Domain," enter the desired domain (e.g., "example.com"). Follow the on-screen instructions to purchase and register the domain. Once registered, a hosted zone for the new domain is automatically created by Amazon. Throughout this guide, refer back to this hosted zone for updating domain records.

### Request an SSL Certificate

To request an SSL certificate through AWS, sign in to the AWS Console and access the AWS Certificate Manager (ACM) service dashboard. Click "Request," and follow the prompts to request a public certificate. When prompted for a fully qualified domain name, enter either a wildcard domain name (e.g., "\*.example.com") to cover the entire domain or a specific subdomain. For multiple HydroServer instances, assign each instance a separate domain or subdomain to prevent routing conflicts. If opting for the wildcard domain name, reuse the certificate for multiple HydroServer instances.

After entering the domain name, select "DNS Validation" as the validation method. Click "Request," then choose the pending certificate from your list. Initiate the creation of necessary CNAME records by clicking "Create records in Route 53" and follow the prompts to validate the certificate.

### Import an SSL Certificate

For existing domains and SSL certificates outside AWS, import the certificate into AWS by navigating to the AWS Certificate Manager (ACM) service dashboard and clicking "Import certificate." Follow the provided instructions to import your certificate into AWS.
