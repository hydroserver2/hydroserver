# Frontend Setup

::: tip Contributing
This guide is for setting up a local development instance of HydroServer which may be useful if you fork our repository and need to modify code. HydroServer is open source, and if you'd like to contribute directly to our repository, checkout our [`contributing guide.`](https://github.com/hydroserver2/hydroserver/blob/main/CONTRIBUTING.md)
:::

## Prerequisites

- Node.js: The frontend uses various Node.js libraries. Check the package.json for specific version requirements.
- npm (typically bundled with Node.js): This is required to install the project's dependencies.

## Installation

1. Clone the repository:

```
git clone https://github.com/hydroserver2/hydroserver-webapp-front.git
```

2. Navigate to the project directory and install the required packages:

```
cd hydroserver-webapp-front
npm install
```

3. Create a .env file in the root of the repository and add variables to match the .env.example file.

4. Build the static files and run the application in production mode:

```
npm run build
npm run preview
```

or developer mode

```
npm run dev
```
