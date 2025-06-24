# How to Customize the Data Management App

We don't want you to have to fork a bunch of repositories when you create and maintain a HydroServer instance, just hydroserver-ops. Therefore, our approach to making the Data Management App customizable is to provide you with a config/ directory in hydroserver-ops where you can update variables and components. When the frontend app is built, it will replace the contents in its config/ directory with the content in your hydroserver-ops directory and populate the website with your custom variables.

For example, if you want an empty map to zoom in to your local area instead of the whole United States, go to config/openLayersMapConfig.ts and change:

```typescript
const defaultLatitude = 39;
const defaultLongitude = -100;
const defaultZoom = 4;
```

to something else.

## Steps to do this

1. Go to the config/ directory in the hydroserver-data-management-app repo in GitHub:

https://github.com/hydroserver2/hydroserver-data-management-app/tree/main/src/config

2. Copy the entire config/ directory and paste it in the root of your hydroserver-ops.

3. Modify the contents of the files you want to customize. Each file has instructions inside for what it can modify.
