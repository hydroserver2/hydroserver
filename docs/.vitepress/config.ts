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
        text: "Guide",
        items: [
          { text: "Getting Started", link: "/guide/getting-started" },
          { text: "Introduction", link: "/guide/introduction" },
          { text: "SensorThings", link: "/guide/sensor-things" },
          { text: "Terminology", link: "/guide/terminology" },
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
        text: "Software Applications",
        items: [
          {
            text: "Data Management App",
            link: "/applications/data-management-app",
          },
          {
            text: "Streaming Data Loader",
            link: "/applications/streaming-data-loader",
          },
          {
            text: "Python Client",
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
