# HydroServer Data Management App Deployment

Before proceeding, set up an environment capable of running NodeJS to build the application code.

While the Data Management App is dependent on the backend application, deploying the Data Management App first is recommended. This approach uses the CloudFront distribution created for the app as a reverse proxy for the backend Elastic Beanstalk deployment.

Start by visiting the [HydroServer Data Management App GitHub repository](https://github.com/hydroserver2/hydroserver-data-management-app). Download the repository or create a fork for codebase modifications or automated deployment using GitHub Actions.

## The Environment File

In the root directory of the local data-management-app repository, create a file named `.env` and add the following settings:

**- VITE_PROXY_BASE_URL**: Set to the desired deployment base URL, including the protocol (e.g., https://hydroserver.example.com).

**- VITE_APP_GOOGLE_MAPS_API_KEY**: Obtain a `Google Maps API key` and place it here for production HydroServer instances.

**- VITE_APP_GOOGLE_MAPS_MAP_ID**: The current version of Google Maps also requires a `MAP ID` in order to style the map to a user's preferences.

**- VITE_APP_GOOGLE_OAUTH_ENABLED**: Set to true or false if you'd like to show or hide the Google OAuth button on the sign in and sign up pages. All this setting does is hide the button. In order to get OAuth working, you'll need to enable it in the hydroserver API services repository as well.

**- VITE_APP_ORCID_OAUTH_ENABLED**: Set to true or false if you'd like to show or hide the ORCID OAuth button on the sign in and sign up pages. Same as Google OAuth, all this setting does is hide the button. In order to get OAuth working, you'll need to enable it in the hydroserver API services repository as well.

**- VITE_APP_HYDROSHARE_OAUTH_ENABLED**: Set to true or false if you'd like to add the frontend functionality of allowing the user to backup their site data to HydroShare. Setting this to true will add a button that links the user's account with a HydroShare account, and various buttons on the Site Details page that will allow them to link a site to a HydroShare resource and schedule archiving.

**- VITE_APP_DISABLE_ACCOUNT_CREATION**: Set to true or false. Setting this to true will completely remove the sign up page, making it so only a system administrator can create accounts through the Django admin panel or command line. Helpful if you'd like your HydroServer instance to be publicly available but you want to restrict who can create an account and add data.

## Build the Vue Application

Run the following commands to install required Node packages and build the application:

```bash
npm install
npm run build
```

This process creates a "dist" directory in the root repository containing the built application, to be uploaded to S3 in the next step.

## S3 Bucket Setup

The Data Management App repository is placed in an S3 bucket, serving as the source for a CloudFront distribution. Access the AWS Console, navigate to the Amazon S3 service dashboard, and click "Create Bucket." Name the bucket appropriately for the frontend distribution and follow default settings, ensuring public access is blocked.

Once the bucket is created, select it and click "Upload" → "Add Files." Navigate to the "dist" folder within the local frontend repository and upload its contents. Note: Upload only the contents of "dist," not the "dist" folder itself.

## CloudFront Distribution Setup

Use CloudFront to serve the HydroServer Data Management App from the S3 bucket. Before setting up the distribution, you need to create an SPA routing function for Vue to function correctly. In the AWS Console, go to the CloudFront service dashboard, select "Functions," and click "Create function." Name the function "spa-routing" and paste the provided code block into the "Function code" section. Click "Save Changes."

```javascript
function handler(event) {
  var request = event.request;
  var uri = request.uri;

  // If the URI ends with a slash or doesn't have a dot, return the main index.html
  if (uri.endsWith("/") || !uri.includes(".")) {
    request.uri = "/index.html";
  }

  return request;
}
```

Return to the CloudFront service dashboard, click "Create distribution," and use default values for distribution settings except for the following:

- Origin Domain: Select the S3 bucket created earlier.
- Origin Access: Choose "Origin access control settings (recommended)," and create control setting with default values.
- Viewer Protocol Policy: Select "Redirect HTTP to HTTPS."
- Viewer Request (Under Function Associations): Choose "CloudFront Functions," then select "spa-routing" for the function ARN/Name.
- Web Application Firewall: Enable security protections.
- Alternate Domain Name (CNAME): Enter the desired HydroServer domain or subdomain.
- Custom SSL Certificate: Select the SSL certificate created or imported in the previous section.

After creating the distribution, a notification will prompt you to update the S3 bucket policy. Click "Copy Policy," navigate to the S3 dashboard, select the associated bucket, click "Permissions," and "Edit" under "Bucket Policy." Paste the policy and click "Save Changes."

Next, create records in Route 53 or other DNS providers pointing to the new CloudFront distribution. For Route 53 users, access the Route 53 service dashboard, select the hosted zone for HydroServer deployment, click "Create record," and configure as follows:

- Record Name: Enter a subdomain (if used), matching the alternate domain name provided to CloudFront.
- Record Type: Select "A."
- Alias: True.
- Route traffic to: Choose "Alias to CloudFront distribution," then select the CloudFront distribution from the dropdown.

Click "Add another record" and configure the second record, selecting "AAAA" as the record type. Click "Create records."

Upon DNS propagation, enter your domain into a browser to view the HydroServer homepage. Note that full functionality requires backend application deployment.
