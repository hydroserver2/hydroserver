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
        collapsed: false,
        link: "/guide/introduction",
        items: [
          { text: "Introduction", link: "/guide/introduction" },
          { text: "Getting Started", link: "/guide/getting-started" },
          {
            text: "Key Concepts",
            collapsed: true,
            items: [
              {
                text: "SensorThings",
                link: "/guide/key-concepts/sensor-things",
              },
              { text: "Site", link: "/guide/key-concepts/sites" },
              { text: "Datastream", link: "/guide/key-concepts/datastreams" },
              {
                text: "Loading Data",
                link: "/guide/key-concepts/loading-data",
              },
              {
                text: "Access Control",
                link: "/guide/key-concepts/access-control",
              },
            ],
          },
        ],
      },
      {
        text: "Tutorials",
        items: [
          {
            text: "HydroServer 101",
            collapsed: true,
            link: "/tutorials/hydroserver-101",
            items: [
              {
                text: "Intro",
                link: "/tutorials/hydroserver-101",
              },
              {
                text: "Creating Your First Site",
                link: "/tutorials/creating-your-first-site",
              },
              {
                text: "Creating Your First Datastream",
                link: "/tutorials/creating-your-first-datastream",
              },
              {
                text: "Creating Your First Orchestration System",
                link: "/tutorials/creating-your-first-orchestration-system",
              },
              {
                text: "Loading Data",
                link: "/tutorials/loading-data",
              },
            ],
          },
        ],
      },
      {
        text: "How-to Guides",
        items: [
          {
            text: "HydroServer 101",
            collapsed: true,
            link: "/tutorials/hydroserver-101",
            items: [
              {
                text: "Intro",
                link: "/tutorials/hydroserver-101",
              },
            ],
          },
        ],
      },
      {
        text: "Data Model",
        items: [
          {
            text: "Data Model Intro",
            link: "/datamodel/data-model",
          },
          {
            text: "Data Dictionary",
            link: "/datamodel/data-dictionary",
          },
        ],
      },
      {
        text: "Client Applications",
        items: [
          {
            text: "Data Management App",
            link: "/applications/data-management-app",
          },
          {
            text: "Python Client",
            collapsed: true,
            link: "/applications/hydroserverpy/overview",
            items: [
              {
                text: "Overview",
                link: "/applications/hydroserverpy/overview",
              },
              {
                text: "Core",
                link: "/applications/hydroserverpy/core",
              },
              {
                text: "ETL",
                link: "/applications/hydroserverpy/etl",
              },
              {
                text: "Quality Control",
                link: "/applications/hydroserverpy/quality_control",
              },
            ],
          },
        ],
      },
      {
        text: "Orchestration Systems",
        items: [
          {
            text: "Overview",
            link: "/orchestration/orchestration-overview",
          },
          {
            text: "Streaming Data Loader",
            link: "/orchestration/streaming-data-loader",
          },
          {
            text: "Airflow Orchestrator",
            link: "/orchestration/airflow-orchestration",
          },
        ],
      },
      {
        text: "APIs",
        items: [
          { text: "SensorThings API", link: "/api/sensor-things-api" },
          { text: "Data Management API", link: "/api/data-management-api" },
          {
            text: "Identity and Access Management API",
            link: "/api/identity-and-access-management-api",
          },
        ],
      },
      {
        text: "Deployment",
        items: [
          {
            text: "Automated AWS Deployment",
            link: "/deployment/aws/manage-aws-deployment",
          },
          {
            text: "Automated GCP Deployment",
            link: "/deployment/gcp/manage-gcp-deployment",
          },
        ],
      },
      {
        text: "Local Development",
        items: [
          { text: "Development Setup", link: "/development/development-setup" },
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
