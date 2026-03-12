# Development Setup

This guide will walk you through setting up HydroServer for local development.

::: tip Contributing
This guide is for setting up a local development instance of HydroServer which may be useful if you fork our repository and need to modify code. HydroServer is open source, and if you'd like to contribute directly to our repository, checkout our [`contributing guide.`](https://github.com/hydroserver2/hydroserver/blob/main/CONTRIBUTING.md)
:::

## Prerequisites

Before starting, make sure you have the following software installed on your machine:
- Python 3.11+
- Docker
- Node.js: The frontend uses various Node.js libraries. Check the package.json for specific version requirements.
- npm (typically bundled with Node.js): This is required to install the project's dependencies.

## NGINX Reverse Proxy and Development Database

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hydroserver2/hydroserver.git
   cd hydroserver/docker/develop
   ```
2. Create environment variables for static and media file paths. The default locations of these folders should be `/static` and `/media` within the `hydroserver-api-services` project folder.
   Mac/Linux:
   ```bash
   export HS_MEDIAFILES="/path/to/media"
   export HS_STATICFILES="/path/to/static"
   ```
   Windows:
   ```cmd
   set HS_MEDIAFILES=C:\path\to\media
   set HS_STATICFILES=C:\path\to\static
   ```
3. Start Docker containers. All services can be accessed in a browser at `http://localhost`.
   ```bash
   docker compose --file "docker-compose.yaml" up
   ```

## HydroServer API Services

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hydroserver2/hydroserver-api-services.git
   cd hydroserver-api-services
   ```
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a .env file in the root of the repository and update variables as needed. For getting started, the default settings should be sufficient.
4. Perform database migrations and collect static files:
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```
5. Create an admin user and load test data.
   ```bash
   python manage.py createsuperuser
   python manage.py load_iam_test_data
   python manage.py load_sta_test_data
   ```
6. Start the development web server:
   ```bash
   python manage.py runserver
   ```

## HydroServer Data Management App

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hydroserver2/hydroserver-data-management-app.git
   ```
2. Navigate to the project directory and install the required packages:
   ```bash
   cd hydroserver-data-management-app
   npm install
   ```
3. Create a .env file in the root of the repository and update variables as needed. For getting started, the default settings should be sufficient.
4. Build the static files and run the application in production mode:
   ```bash
   npm run build
   npm run preview
   ```
   or developer mode
   ```bash
   npm run dev
   ```
