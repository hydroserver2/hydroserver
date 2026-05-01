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
        link: "/introduction/introduction",
        items: [
          {
            text: "Introduction",
            link: "/introduction/introduction",
          },
          { text: "Background", link: "/introduction/background" },
          { text: "Getting Started", link: "/introduction/getting-started" },
          {
            text: "Key Concepts",
            collapsed: true,
            link: "/introduction/key-concepts/key-concepts",
            items: [
              { text: "Site", link: "/introduction/key-concepts/sites" },
              {
                text: "Datastream",
                link: "/introduction/key-concepts/datastreams",
              },
              {
                text: "Observations",
                link: "/introduction/key-concepts/observations",
              },
              {
                text: "Workspaces and Access Control",
                link: "/introduction/key-concepts/workspaces-access-control",
              },
              {
                text: "Identifiers",
                link: "/introduction/key-concepts/identifiers",
              },
            ],
          },
        ],
      },
      {
        text: "Tutorials",
        collapsed: true,
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
          {
            text: "Getting Started with hydroserver.ts",
            link: "/tutorials/getting-started-with-hydroserver-ts",
          },
          // {
          //   text: "hydroserverpy 101",
          //   collapsed: true,
          //   link: "/tutorials/hydroserverpy/hydroserverpy-101",
          //   items: [
          //     {
          //       text: "Intro",
          //       link: "/tutorials/hydroserverpy/hydroserverpy-101",
          //     },
          //   ],
          // },
        ],
      },
      {
        text: "How-to",
        collapsed: true,
        items: [
          // {
          //   text: "Data Management App",
          //   collapsed: true,
          //   link: "/how-to/data-management-app/customize.md",
          //   items: [
          //     {
          //       text: "Customize the Data Management App",
          //       link: "/how-to/data-management-app/customize.md",
          //     },
          //     // {
          //     //   text: "Archive Data to HydroShare",
          //     //   link: "/how-to/data-management-app/hydroshare-archive.md",
          //     // },
          //   ],
          // },
          {
            text: "Deployment",
            collapsed: true,
            link: "/how-to/deployment/gcp/manage-gcp-deployment",
            items: [
              {
                text: "Local Development Guide",
                link: "/how-to/development/development-setup",
              },
              {
                text: "Production Deployment Guide",
                link: "/how-to/deployment/production-deployment-overview",
              },
            ],
          },
          {
            text: "Python Client",
            collapsed: true,
            link: "/how-to/hydroserverpy/hydroserverpy-examples",
            items: [
              {
                text: "Manage Data With Hydroserverpy",
                link: "/how-to/hydroserverpy/hydroserverpy-examples",
              },
              // {
              //   text: "Extract, transform and load with Hydroserverpy",
              //   link: "/how-to/hydroserverpy/etl",
              // },
            ],
          },
          {
            text: "TypeScript Client",
            collapsed: true,
            link: "/how-to/typescript-client/typescript-client-examples",
            items: [
              {
                text: "Manage Data With the TypeScript Client",
                link: "/how-to/typescript-client/typescript-client-examples",
              },
            ],
          },
          {
            text: "SensorThings API",
            collapsed: true,
            link: "/how-to/sensor-things/retrieve-sensor-things",
            items: [
              {
                text: "Retrieve Data With the SensorThings API",
                link: "/how-to/sensor-things/retrieve-sensor-things",
              },
              {
                text: "Post Data With the SensorThings API",
                link: "/how-to/sensor-things/post-sensor-things",
              },
            ],
          },
        ],
      },
      {
        text: "References",
        collapsed: true,
        items: [
          {
            text: "API",
            link: "/references/api/api-ref.md",
          },
          {
            text: "Data Model",
            collapsed: true,
            link: "/references/data-model/data-model",
            items: [
              {
                text: "Data Dictionary",
                link: "/references/data-model/data-dictionary",
              },
            ],
          },
          {
            text: "Hydroserverpy",
            link: "/references/hydroserverpy/hydroserverpy-ref.md",
          },
          {
            text: "Streaming Data Loader",
            link: "/references/orchestration/sdl-download",
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
