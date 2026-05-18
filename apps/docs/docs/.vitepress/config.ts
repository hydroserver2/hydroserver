import { defineConfig } from "vitepress";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "HydroServer",
  description: "The official docs for HydroServer",
  base: "/hydroserver/",
  head: [
    [
      "link",
      {
        rel: "icon",
        href: "/hydroserver/favicon.ico",
      },
    ],
  ],
  themeConfig: {
    logo: "/logo.png",
    // https://vitepress.dev/reference/default-theme-config
    nav: [{ text: "Home", link: "/" }],

    sidebar: [
      {
        text: "Introduction",
        collapsed: true,
        link: "/introduction/",
        items: [
          { text: "HydroServer Overview", link: "/introduction/hydroserver-overview" },
          { text: "Background & Motivation", link: "/introduction/background-and-motivation" },
          { text: "Getting Started", link: "/introduction/getting-started" },
          {
            text: "Key Concepts",
            collapsed: true,
            link: "/introduction/key-concepts/",
            items: [
              {
                text: "Workspaces and Access Control",
                link: "/introduction/key-concepts/workspaces-and-access-control",
              },
              { text: "Monitoring Sites", link: "/introduction/key-concepts/monitoring-sites" },
              {
                text: "Datastreams",
                link: "/introduction/key-concepts/datastreams",
              },
              {
                text: "Observations",
                link: "/introduction/key-concepts/observations",
              },
              {
                text: "Resource Identifiers",
                link: "/introduction/key-concepts/resource-identifiers",
              },
            ],
          },
        ],
      },
      {
        text: "User Guides",
        collapsed: true,
        link: "/user-guides/",
        items: [
          {
            text: "Tutorials",
            collapsed: true,
            link: "/user-guides/tutorials/",
            items: [
              {
                text: "HydroServer 101",
                collapsed: true,
                link: "/user-guides/tutorials/hydroserver-101/",
                items: [
                  {
                    text: "Creating Your First Site",
                    link: "/user-guides/tutorials/hydroserver-101/creating-your-first-site",
                  },
                  {
                    text: "Creating Your First Datastream",
                    link: "/user-guides/tutorials/hydroserver-101/creating-your-first-datastream",
                  },
                  {
                    text: "Creating Your First Orchestration System",
                    link: "/user-guides/tutorials/hydroserver-101/creating-your-first-orchestration-system",
                  },
                  {
                    text: "Loading Observations into a Datastream",
                    link: "/user-guides/tutorials/hydroserver-101/loading-observations-into-a-datastream",
                  }
                ]
              },
              {
                text: "Set Up Automated Data Ingestion with Python",
                link: "/user-guides/tutorials/set-up-automated-data-ingestion-with-python",
              }
            ]
          },
          {
            text: "How-to",
            collapsed: true,
            link: "/user-guides/how-to/",
            items: [
              {
                text: "Creating User Accounts",
                link: "/user-guides/how-to/creating-user-accounts",
              },
              {
                text: "Managing Workspaces",
                link: "/user-guides/how-to/managing-workspaces",
              },
              {
                text: "Managing Access Control",
                link: "/user-guides/how-to/managing-access-control",
              },
              {
                text: "Managing Site Metadata",
                link: "/user-guides/how-to/managing-site-metadata",
              },
              {
                text: "Managing Datastream Metadata",
                link: "/user-guides/how-to/managing-datastream-metadata",
              },
              {
                text: "Loading Data",
                link: "/user-guides/how-to/loading-data",
              },
              {
                text: "Visualizing Data",
                link: "/user-guides/how-to/visualizing-data",
              },
              {
                text: "Exporting and Downloading Data",
                link: "/user-guides/how-to/exporting-and-downloading-data",
              },
              {
                text: "Archiving Data to HydroShare",
                link: "/user-guides/how-to/archiving-data-to-hydroshare",
              },
              {
                text: "Using the Python Client",
                link: "/user-guides/how-to/using-the-python-client",
              },
              {
                text: "Loading Data with the SensorThings API",
                link: "/user-guides/how-to/loading-data-with-sensorthings",
              },
              {
                text: "Retrieving Data with the SensorThings API",
                link: "/user-guides/how-to/retrieving-data-with-sensorthings",
              }
            ]
          }
        ]
      },
      {
        text: "Developing & Contributing",
        collapsed: true,
        link: "/developing-and-contributing/",
        items: [
          {
            text: "Tutorials",
            collapsed: true,
            link: "/developing-and-contributing/tutorials/",
            items: [
              {
                text: "Building Your First App",
                link: "/developing-and-contributing/tutorials/building-your-first-app",
              }
            ]
          },
          {
            text: "How-to",
            collapsed: true,
            link: "/developing-and-contributing/how-to/",
            items: [
              {
                text: "Setting Up a Development Environment",
                link: "/developing-and-contributing/how-to/setting-up-a-development-environment",
              },
              {
                text: "Using the TypeScript Client",
                link: "/developing-and-contributing/how-to/using-the-typescript-client",
              },
            ]
          }
        ]
      },
      {
        text: "Hosting & Deployment",
        collapsed: true,
        link: "/hosting-and-deployment/",
        items: [
          {
            text: "Tutorials",
            collapsed: true,
            link: "/hosting-and-deployment/tutorials/",
            items: [
              {
                text: "Deploying to Google Cloud Platform",
                link: "/hosting-and-deployment/tutorials/deploying-to-google-cloud-platform",
              },
              {
                text: "Deploying to Amazon Web Services",
                link: "/hosting-and-deployment/tutorials/deploying-to-amazon-web-services",
              },
              {
                text: "Deploying with Docker Compose",
                link: "/hosting-and-deployment/tutorials/deploying-with-docker-compose",
              },
            ]
          },
          {
            text: "How-to",
            collapsed: true,
            link: "/hosting-and-deployment/how-to/",
            items: [
              {
                text: "Setting Up a Production Deployment",
                link: "/hosting-and-deployment/how-to/setting-up-a-production-deployment",
              },
              {
                text: "Using the Administrator Dashboard",
                link: "/hosting-and-deployment/how-to/using-the-administrator-dashboard",
              },
            ]
          }
        ]
      },
      {
        text: "References",
        collapsed: true,
        link: "/references/",
        items: [
          {
            text: "Data Model",
            link: "/references/data-model",
          },
          {
            text: "Data Dictionary",
            link: "/references/data-dictionary",
          },
          {
            text: "HydroServer APIs",
            link: "/references/hydroserver-apis",
          },
          {
            text: "Streaming Data Loader",
            link: "/references/streaming-data-loader",
          },
        ],
      },
    ],

    socialLinks: [
      { icon: "github", link: "https://github.com/hydroserver2/hydroserver" },
    ],

    search: {
      provider: "local",
    },
  },
});
