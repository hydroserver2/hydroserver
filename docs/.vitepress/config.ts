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
          { text: "HydroServer Web App", link: "/guide/web-application" },
          { text: "Loading Data", link: "/guide/loading-data" },
        ],
      },
      {
        text: "APIs",
        items: [
          { text: "SensorThings API", link: "/api/sensor-things-api" },
          { text: "Data Management API", link: "/api/data-management-api" },
          {
            text: "Account Management API",
            link: "/api/account-management-api",
          },
        ],
      },
      {
        text: "Deployment",
        items: [
          { text: "Automated AWS and Timescale Cloud Deployment", link: "/deployment/aws-deployment-terraform" },
          {
            text: "Manual AWS Deployment",
            link: "/deployment/aws-deployment",
            items: [
              {
                text: "Intro and Registration",
                link: "/deployment/aws-deployment",
              },
              {
                text: "Frontend Deployment",
                link: "/deployment/frontend-deployment",
              },
              {
                text: "Backend Deployment",
                link: "/deployment/backend-deployment",
              },
            ],
          },
          { text: "Manual Timescale Cloud Deployment", link: "/deployment/timescale-cloud" },
        ],
      },
      {
        text: "Local Development",
        items: [
          { text: "Frontend Setup", link: "/development/frontend-setup" },
          { text: "Backend Setup", link: "/development/backend-setup" },
        ],
      },
    ],

    socialLinks: [
      { icon: "github", link: "https://github.com/hydroserver2/hydroserver" },
    ],
  },
});
