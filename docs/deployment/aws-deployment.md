# HydroServer AWS Deployment

## AWS Required Services

Before reading this guide, you should set up an AWS account and be familiar with basic concepts of cloud security. It is
recommended that any roles and policies you use to set up and manage these services are appropriately scoped.

There are several ways to deploy websites and applications to AWS. The HydroServer AWS deployment described in this 
guide will use the following AWS services:

- CloudFront
- Elastic Beanstalk
- EC2 (Load Balancers)
- Amazon S3
- Amazon SES

This guide will also describe how to set up an AWS managed domain for HydroServer if you don't already have one set up.
If you want to set up a domain with AWS, you will also use the following services:

- Route 53
- AWS Certificate Manager (ACM)

## AWS Domain Registration and Certificate Requests

This section will briefly cover how register a domain and set up SSL certificates. If you already have a domain and SSL
certificate you can skip to the next section to learn how to import your SSL certificate into AWS. For a more detailed 
walkthrough on domain registration and certificate requests, you can visit these pages:

- [Registering a new domain](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html)
- [Requesting a public certificate](https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html)

### Register a Domain

To set up an AWS managed domain, sign in to the AWS Console and go to the Route 53 service dashboard. Under "Register 
Domain", enter the domain you want to register (such as "example.com"). From there, follow the instructions on the page
to purchase and register the domain. Once the domain is registered, Amazon should have automatically created a hosted
zone for your new domain. You'll refer back to this hosted zone throughout this guide to update domain records.

### Request an SSL Certificate

To request an SSL certificate through AWS, sign in to the AWS Console and go to the AWS Certificate Manager (ACM)
service dashboard. Click "Request", then follow the prompts to request a public certificate. When you're asked to enter
a fully qualified domain name, you can either enter a wildcard domain name (such as "*.example.com") if you want the 
certificate to cover your whole domain, or you can enter a specific subdomain. If you want to run multiple instances
of HydroServer, each instance should be assigned a separate domain or subdomain to avoid routing conflicts. If you
choose the wildcard domain name option, this certificate can be reused for multiple HydroServer instances.

After entering a fully qualified domain name, you should choose "DNS Validation" for the validation method. Click
"Request", then select the certificate from your list of certificates. It should have a status of "Pending validation".
Click "Create records in Route 53" and follow the prompts to automatically create the necessary CNAME record to validate
the certificate.

### Import an SSL Certificate

If you have a domain and SSL certificate set up outside AWS, you can import the certificate into AWS by going to the AWS
Certificate Manager (ACM) service dashboard and clicking "Import certificate". Follow the instructions to import your 
certificate into AWS.


## HydroServer Frontend Deployment

This section will cover how to deploy the HydroServer Vite frontend application on AWS. Before you continue, you'll need
set up an environment where you can run NodeJS to build the application code.

Even though the frontend is dependent on the backend application, it's easier to deploy the frontend first because 
you'll use the CloudFront distribution you create for the frontend as a reverse proxy for the backend Elastic Beanstalk 
deployment as well. First, go to the 
[HydroServer frontend GitHub repository](https://github.com/hydroserver2/hydroserver-webapp-front) and download the 
repository, or create a fork if you want to modify the codebase or use GitHub Actions for automated deployment.

### Build the Vite Application

In the root directory of your local copy of the frontend repository, create a file called ".env". In this file add the 
following settings:
- VITE_PROXY_BASE_URL: The value should be the domain you want to use as the base URL of your deployment, including the
desired protocol (e.g. https://hydroserver.example.com).
- VITE_APP_GOOGLE_MAPS_API_KEY: You should obtain a Google Maps API key and place it here if you're deploying a
production instance of HydroServer.

Run the following command to install all required Node packages:

```
npm install
```

Next, run the following command to build the application:

```
npm run build
```

The previous command created a directory called "dist" in your root repo directory that contains your built application, 
and is what you will upload to S3 in the next step.


### S3 Bucket Setup

Your frontend repository will be placed in an S3 bucket where it will be served by a CloudFront distribution. Sign in
to the AWS Console and go to the Amazon S3 service dashboard. Click "Create Bucket". This bucket will be used
exclusively for the frontend distribution, so name it accordingly. You'll add bucket policies later, so for now create
the bucket with default settings. Be sure all public access is blocked.

After the bucket is created, select it from you list and then click "Upload" &rarr; "Add Files". Navigate to the "dist" 
folder inside your local frontend repository that you created in the previous section and select all contents of that
directory to upload. Note: Be sure to only upload the contents of "dist", not the "dist" folder itself.

### CloudFront Distribution Setup

You'll use CloudFront to serve the HydroServer frontend application from the S3 bucket you just created. Before you set
up the distribution, you need to create a SPA routing function for Vite to work correctly. From the AWS Console, go to 
the CloudFront service dashboard, select "Functions" from the navigation pane, and click "Create function". The name of
this function should be "spa-routing". When you create the function, paste the following block of code into the
"Function code" section, overwriting the default code block, then click "Save Changes".

```
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    // If the URI ends with a slash or doesn't have a dot, return the main index.html
    if (uri.endsWith('/') || !uri.includes('.')) {
        request.uri = '/index.html';
    }

    return request;
}
```

Once you've finished creating the SPA Routing function, go back to the CloudFront service dashboard and click 
"Create distribution". You can use default values for the distribution settings except for the following:

- Origin Domain: Select the S3 bucket you created in the previous step.
- Origin Access: Select "Origin access control settings (recommended)", then click "Create control setting" with default
values.
- Viewer Protocol Policy: Select "Redirect HTTP to HTTPS"
- Viewer Request (Under Function Associations): Select "CloudFront Functions" for the function type, then select 
"spa-routing" for the function ARN/Name (This is the function you created in the previous step).
- Web Application Firewall: Select "Enable security protections"
- Alternate Domain Name (CNAME): Enter the domain or subdomain you want to use for HydroServer.
- Custom SSL Certificate: Select the SSL certificate you created or imported in the previous section.

After you create the distribution, you'll see a notification that you need to update the S3 bucket policy. Click "Copy
Policy", then navigate to your S3 dashboard and select the bucket you linked to the CloudFront distribution. Click 
"Permissions", then "Edit" under "Bucket Policy". Paste the policy here, then click "Save Changes".

Next, you'll need to create records in Route 53 or other DNS provider that point to your new CloudFront distribution. 
If you used Route 53, you should go to the Route 53 service dashboard and select the hosted zone you're
using for your HydroServer deployment. Click "Create record", and enter the following configuration:

- Record Name: Enter  subdomain if you want to use one. It must match the alternate domain name you provided to 
CloudFront.
- Record Type: Select "A"
- Alias: True
- Route traffic to: Select "Alias to CloudFront distribution", then select your CloudFront distribution from the 
dropdown.

After entering the configuration, click "Add another record", and use the same configuration as the first record, except
select "AAAA" as the record type instead of "A". Click "Create records".

Once the records have been created and pushed to DNS servers, you should be able to enter your domain into a browser and
see the HydroServer homepage. Remember that the site will not be fully functional until you deploy the backend
application.


## HydroServer Backend Deployment

This section will cover how to deploy the HydroServer Django API application on AWS. First, go to the [HydroServer
backend GitHub repository](https://github.com/hydroserver2/hydroserver-webapp-back) and download the repository, or 
create a fork if you want to modify the codebase or use GitHub Actions for automated deployment. You may want to 
follow the instructions to set up a development environment on your local machine before continuing.

Before you deploy the application, you'll want to create a zip archive of your copy of the backend HydroServer 
repository. Depending on your platform, you may want to exclude certain hidden files from the zipped repository that 
can cause issues (such as .DS_Store on macOS, your .git folder, and your local .env file for example).


### Elastic Beanstalk Setup

Once you have access to the backend repository, sign in to the AWS Console and go to the Elastic Beanstalk service 
dashboard. This service will be used to run the Django API application. Select "Applications", then click "Create 
application". If you want to deploy multiple instances of the app, you can create one application for multiple 
environments, or one application for each environment depending on how you want to handle versioning.

Once you create the application, from the application's landing page you'll click "Create new 
environment". The environment setup process includes several pages of configuration. The default options are generally
sufficient for the initial environment setup, but you should pay attention to the following settings:

- Environment Tier: Select "Web server environment" for this application.
- Domain: You can provide a domain name if you want, but this autogenerated domain will only be temporary. Take note of
  this value for later.
- Platform and Branch: Select "Python" for the platform and "Python 3.8" for the branch.
- Application Code: Choose "Upload you code" and select the zip file you created in the previous step.
- Service Role: Create or select an IAM service role to manage this application.
- EC2 Key Pair: Create or select an EC2 pair for this environment. You'll need this to be able to connect to your 
instance via SSH.
- Database: It is recommended that you set up the database instance separately from the application environment either
through Timescale Cloud or Amazon RDS. If you set up the database here, you may lose data if you ever need to rebuild
the environment.
- Auto Scaling Group: You should select "Load balanced", even if you want to limit the environment to one instance. This
will create an EC2 Application Load Balancer container that you'll use to connect to CloudFront in a later step.
- Listeners: These will be updated later, but for now the default listener on port 80 is sufficient.
- Environment Properties: Add the following environment properties in addition to the default PYTHONPATH:
    * DEPLOYED: True
    * DEBUG: Set this to True for testing and development environments; otherwise set it to False.
    * AWS_ACCESS_KEY_ID: Enter an access key that will be used to read and write static and media files to AWS S3 and send
    admin emails through Amazon SES for account verification and password reset.
    * AWS_SECRET_ACCESS_KEY: Enter the corresponding secret key.
    * AWS_STORAGE_BUCKET_NAME: Enter the name of the bucket you want to use to host static files.
    * DATABASE_URL: Enter the URL for the database service you want to use. If you set up a Timescale Cloud
    instance, the pattern would be: 
    postgresql://{db_user}:{db_password}.{db_host}:{db_port}/tsdb
    * SECRET_KEY: Generate a random secret key string to use for Django.
    * PROXY_BASE_URL: Enter the domain value from earlier (e.g. http://my-hs-env.us-east-1.elasticbeanstalk.com)
    * ALLOWED_HOSTS: Enter the domain value from earlier without the protocol 
      (e.g. my-hs-env.us-east-1.elasticbeanstalk.com)

After you finish creating your environment, you will be taken to the environment landing page. The environment will take
several minutes to start up. From here you can monitor the health of the environment, access logs, and update
configuration settings if needed. If everything ran successfully, after a few minutes the environment should display a
health status of "Ok". If it doesn't you may need to check the logs and revisit your environment configuration to
resolve the issue.

To further verify that your environment started successfully, check the /admin/ endpoint of your temporary Elastic 
Beanstalk domain. You should see an administrator login page.


### CloudFront Setup

Before you continue, you should have already set up a CloudFront distribution to deploy the HydroServer frontend. You'll
use the same distribution to connect to the backend Elastic Beanstalk environment.

Log in to the AWS Console and go to the CloudFront service dashboard. Select the CloudFront distribution you created
earlier, then select "Origins" and click "Create origin". Use the following configuration options for this origin:

- Origin Domain: Under "Elastic Load Balancer" select the load balancer being used for your Elastic Beanstalk
environment. If you don't know the name, you can go to the events log on the Elastic Beanstalk environment landing page
and search for "Created Load Balancer". The name of the load balancer should be included in that log entry.
- Protocol: Select "HTTP only"

After you create the new origin, select "Behaviors" from the distribution landing page. You'll need to create three
behaviors with the following configurations:

1. SensorThings API
   - Path Pattern: /api/sensorthings/*
   - Origin and Origin Groups: Select your load balancer
   - Viewer Protocol Policy: HTTP and HTTPS
   - Allowed HTTP Methods: GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE
   - Cache Policy: CachingDisabled
   - Origin Request Policy: AllViewer
2. Data Management API
   - Path Pattern: /api/*
   - Origin and Origin Groups: Select your load balancer
   - Viewer Protocol Policy: Redirect HTTP to HTTPS
   - Allowed HTTP Methods: GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE
   - Cache Policy: CachingDisabled
   - Origin Request Policy: AllViewer
3. Admin Dashboard
   - Path Pattern: /admin/*
   - Origin and Origin Groups: Select your load balancer
   - Viewer Protocol Policy: Redirect HTTP to HTTPS
   - Allowed HTTP Methods: GET, HEAD
   - Cache Policy: CachingDisabled
   - Origin Request Policy: AllViewer

Once you've created these behaviors, make sure that they appear in the list in the following order by path pattern:

1. /api/sensorthings/*
2. /api/*
3. /admin/*
4. Default (*)

If you ever need to add static files or other media files for Django, you can add additional behaviors here to point to
their respective S3 buckets.

Before you can access the Django API on your domain, you need to update some security settings on your load balancer
to allow traffic to pass between CloudFront and Elastic Beanstalk. Go to the EC2 service dashboard in the AWS Console,
select "Target Groups" from the navigation pane, then click "Create Target Group". Create a target group with the
following configuration:

- Target Type: Select "Instances"
- Target Group Name: Enter a name you can use to identify this target group
- Protocol: Select "HTTPS"; the port should be set to 443.
- Health Check Protocol: Select "HTTPS"
- Targets: Select your HydroServer Elastic Beanstalk instance.

Next, select "Load balancers" from the navigation pane, then select the load balancer associated with the HydroServer 
Elastic Beanstalk instance. Under "Listeners and rules" click "Add Listener" and create a listener with the following 
configuration options:

- Protocol: Select "HTTPS"; the port should be set to 443.
- Target Group: Select the target group you just created.
- Default SSL/TLS Certificate: Select the certificate you're using for this deployment.

After you create the listener, select "Security Groups" from the navigation pane. You should see two security groups
associated with your Elastic Beanstalk environment. Select the security group that only has one permission entry. The
description should be "Elastic Beanstalk created security group used when no ELB security groups are specified during 
ELB creation." Click "Edit inbound rules", then "Add rule". The type for the new rule should be "HTTPS" and the source
should be "Anywhere-IPv4"

Finally, return to your Elastic Beanstalk environment page and click "Configuration", then "Edit" under "Updates, 
monitoring, and logging". Change the PROXY_BASE_URL environment property to your domain with the https protocol, and
change the ALLOWED_HOSTS environment property to your domain without any protocol, then click "Apply". After your 
environment finishes updating with the new environment properties, you can check that the Django app is accessible
on your domain by entering the domain with the path /admin/ in a browser. If everything is configured correctly, you
should see an admin login page.

### Amazon SES Setup

HydroServer requires Amazon SES to be able to send account verification and password reset emails. Before you can create
an account on your deployed HydroServer instance, you'll need to set up SES for your domain.

Log in to the AWS Console and go to the Amazon SES service dashboard. Click "Create identity" and follow the prompts to
link Amazon SES to your domain. Once you have Amazon SES set up, go back to your Elastic Beanstalk environment page 
and click "Configuration", then "Edit" under "Updates, monitoring, and logging". Add an environment property called
ADMIN_EMAIL and set it to an address associated with the SES identity you just created, such as "admin@example.com".
This email address will be used to send account verification and password reset emails to users.

Note: By default, your Amazon SES identity will be set up in sandbox mode, so you'll need to verify all email addresses
you want to send messages to. You need to contact Amazon and go through their verification process to be removed from
sandbox mode.

At this point, you should have both the frontend and backend HydroServer applications deployed. Enter the domain you
used to deploy HydroServer into a browser and begin using the site.
