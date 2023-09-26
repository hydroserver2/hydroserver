import { defineConfig } from "vitepress";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "HydroServer",
  description: "The official docs for HydroServer",
  base: "/hydroserver/",
  themeConfig: {
    logo: "/logo.png",
    // https://vitepress.dev/reference/default-theme-config
    nav: [{ text: "Home", link: "/" }],

    sidebar: [
      {
        text: "Guide",
        items: [
          { text: "Introduction", link: "/guide/introduction" },
          { text: "Getting Started", link: "/guide/getting-started" },
          { text: "Loading Data", link: "/guide/loading-data" },
        ],
      },
      {
        text: "APIs",
        items: [
          { text: "SensorThings API", link: "/api/sensor-things-api" },
          { text: "Data Management API", link: "/api/data-management-api" },
        ],
      },
      {
        text: "Deployment",
        items: [
          { text: "Amazon Web Services", link: "/deployment/aws-deployment" },
          { text: "Timescale Cloud", link: "/deployment/timescale-cloud" },
        ],
      },
    ],

    socialLinks: [
      { icon: "github", link: "https://github.com/hydroserver2/hydroserver" },
    ],
  },
});
