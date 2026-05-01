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
        link: "/tutorials/tutorials",
        items: [
          {
            text: "HydroServer 101",
            collapsed: true,
            link: "/tutorials/hydroserver-101",
            items: [
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
        link: "/how-to/how-to",
        items: [
          {
            text: "Load Data",
            collapsed: true,
            link: "/how-to/load-data/loading-data",
            items: [
              {
                text: "Data Ingestion with hydroserverpy",
                link: "/how-to/load-data/etl",
              },
            ],
          },
          {
            text: "Archive Data to HydroShare",
            link: "/how-to/hydroshare-archive/hydroshare-archive",
          },
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
            link: "/how-to/deployment/production-deployment-overview",
            items: [
              {
                text: "Local Development Guide",
                link: "/how-to/development/development-setup",
              },
            ],
          },
          {
            text: "Python Client",
            link: "/how-to/hydroserverpy/hydroserverpy-examples",
          },
          {
            text: "TypeScript Client",
            link: "/how-to/typescript-client/typescript-client-examples",
          },
          {
            text: "SensorThings API",
            collapsed: true,
            link: "/how-to/sensor-things/retrieve-sensor-things",
            items: [
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
        link: "/references/references",
        items: [
          {
            text: "API",
            link: "/references/api/api-ref",
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
            link: "/references/hydroserverpy/hydroserverpy-ref",
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
