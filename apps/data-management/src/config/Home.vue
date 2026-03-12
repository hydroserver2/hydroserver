<template>
  <div class="banner">
    <div
      class="d-flex text-white flex-column align-center text-center fill-height justify-space-between py-12"
    >
      <div>
        <img
          :src="hydroWhiteImg"
          alt="Hydro Logo"
          style="max-width: 500px; width: 100%"
        />
        <h4 class="text-h4 mb-8 has-text-shadow">
          Collect and Manage Your Operational Hydrologic Data
        </h4>
      </div>

      <div v-if="hs.session.isAuthenticated">
        <h5 class="text-h5 mb-8 has-text-shadow">
          Logged in as {{ user?.firstName }}
          {{ user?.lastName }}
        </h5>
      </div>
      <div v-else-if="disableAccountCreation !== 'true'">
        <h5 class="text-h5 mb-8 has-text-shadow">
          Create an account to get started
        </h5>
        <v-btn-primary to="/sign-up">Sign Up</v-btn-primary>
      </div>
    </div>
  </div>

  <v-container class="my-8">
    <div class="d-flex flex-column align-center text-center">
      <h2 class="text-h4 mb-4">Manage your Operational Data</h2>

      <p class="mb-8 text-body-1 text-medium-emphasis">
        The HydroServer Hydrologic Information System provides services and
        tools for collecting, storing, managing, and sharing your hydrologic
        observations collected from in situ monitoring sites.
      </p>
    </div>

    <v-row>
      <v-col cols="12" sm="6" class="mb-4">
        <div class="d-flex flex-column flex-sm-row text-center text-sm-left">
          <div class="text-center mr-4">
            <v-icon :icon="mdiResistor" size="4rem" />
          </div>
          <div>
            <p class="text-body-1 font-weight-bold mb-2">
              Sensor Data Streaming
            </p>
            <p class="text-body-2 text-medium-emphasis mb-2">
              Stream sensor data directly from your Internet connected
              datalogger or load data using our Streaming ETL System software.
            </p>
          </div>
        </div>
      </v-col>

      <v-col cols="12" sm="6" class="mb-4">
        <div class="d-flex flex-column flex-sm-row text-center text-sm-left">
          <div class="text-center mr-4">
            <v-icon :icon="mdiDatabaseOutline" size="4rem" />
          </div>
          <div>
            <p class="text-body-1 font-weight-bold mb-2">
              Performant Data Storage
            </p>
            <p class="text-body-2 text-medium-emphasis mb-2">
              Using TimeScale DB with PostgreSQL, we provide a performant data
              store for your operational data.
            </p>
          </div>
        </div>
      </v-col>

      <v-col cols="12" sm="6" class="mb-4">
        <div class="d-flex flex-column flex-sm-row text-center text-sm-left">
          <div class="text-center mr-4">
            <v-icon :icon="mdiCogOutline" size="4rem" />
          </div>
          <div>
            <p class="text-body-1 font-weight-bold mb-2">
              Easy Web Configuration
            </p>
            <p class="text-body-2 text-medium-emphasis mb-2">
              Create new monitoring locations, observed variables, sensors, and
              data streams through our web user interface.
            </p>
          </div>
        </div>
      </v-col>

      <v-col cols="12" sm="6" class="mb-4">
        <div class="d-flex flex-column flex-sm-row text-center text-sm-left">
          <div class="text-center mr-4">
            <v-icon :icon="mdiLockOpenOutline" size="4rem" />
          </div>
          <div>
            <p class="text-body-1 font-weight-bold mb-2">
              Public Access to Your Data
            </p>
            <p class="text-body-2 text-medium-emphasis mb-2">
              Provide convenient and simple access to the data from your
              monitoring sites.
            </p>
          </div>
        </div>
      </v-col>
    </v-row>
  </v-container>

  <v-divider></v-divider>

  <v-container class="my-8">
    <v-row>
      <v-col
        class="d-flex flex-column justify-center align-center"
        cols="12"
        sm="5"
        order="last"
        order-sm="first"
      >
        <v-img
          :src="noaaLogo"
          max-width="12rem"
          class="mb-8"
          width="100%"
          alt="NOAA Logo"
        ></v-img>
        <v-img
          :src="owpLogo"
          max-width="18rem"
          width="100%"
          alt="OWP Logo"
        ></v-img>
      </v-col>
      <v-col class="d-flex justify-center flex-column" cols="12" sm="7">
        <h4 class="text-h4 mb-4">Operational Data for Modeling</h4>
        <p class="text-body-1 mb-2 font-weight-bold">
          Your data can improve NOAA's water prediction services
        </p>
        <p class="text-body-1 text-medium-emphasis">
          NOAA's National Water Model can assimilate streamflow data from
          operational monitoring sites like yours. Contribute your streamflow
          data to make it available to support continental-scale hydrologic
          modeling and forecasting via the National Water Model.
        </p>
      </v-col>
    </v-row>
  </v-container>

  <v-divider></v-divider>

  <v-container class="my-8">
    <v-row>
      <v-col class="d-flex flex-column justify-center" cols="12" sm="6">
        <h4 class="text-h4 mb-8">Open Standards Data Sharing</h4>
        <p class="text-body-1 text-medium-emphasis">
          Share your data publicly using the latest Open Geospatial Consortium
          web services standard SensorThings.
        </p>
        <div>
          <v-img
            :src="ogcLogo"
            max-width="26rem"
            height="auto"
            alt="OGC Logo"
          ></v-img>
        </div>
      </v-col>
      <v-col cols="12" sm="6" class="d-flex flex-column align-center">
        <v-img
          :src="sensorThingsLogo"
          width="100%"
          max-width="35rem"
          alt="SensorThings Database Schema"
        ></v-img>
        <h4 class="text-h4">SensorThings</h4>
      </v-col>
    </v-row>
  </v-container>

  <v-divider> </v-divider>

  <v-container class="d-flex flex-column align-center my-8">
    <v-img
      :src="cirohLogo"
      class="mb-8"
      width="100%"
      max-width="14rem"
      alt="CIROH Logo"
    ></v-img>
    <p class="text-body-1 text-medium-emphasis text-center">
      This HydroServer instance is supported through the Cooperative Institute
      for Research to Operations in Hydrology (CIROH)
    </p>
  </v-container>
</template>

<script setup lang="ts">
/**
 * The purpose of this file is to provide an example landing page for your HydroServer instance.
 * By default, the home page is disabled and navigating to '/' will redirect to the /browse page.
 * To enable the home page, set enableHomePage to true in homeConfig.ts then modify this file
 * as you wish.
 */
import noaaLogo from '@/assets/noaa-min.png'
import owpLogo from '@/assets/owp-min.png'
import ogcLogo from '@/assets/ogc-min.png'
import cirohLogo from '@/assets/CIROH_logo_transparent-min.png'
import sensorThingsLogo from '@/assets/sensorThings-min.png'
import hydroWhiteImg from '@/assets/hydroserver-white-min.png'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/store/user'
import hs from '@hydroserver/client'
import {
  mdiCogOutline,
  mdiDatabaseOutline,
  mdiLockOpenOutline,
  mdiResistor,
} from '@mdi/js'

const { user } = storeToRefs(useUserStore())
const disableAccountCreation =
  import.meta.env.VITE_APP_DISABLE_ACCOUNT_CREATION || 'false'
</script>

<style scoped lang="scss">
.v-container {
  max-width: 1200px;
}

p {
  max-width: 40rem;
}

.has-text-shadow {
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.65);
}

$gradient: linear-gradient(
    180deg,
    rgba(55, 104, 155, 0.47) 10%,
    rgb(21 40 61 / 36%) 65%,
    #00051ab0
  ),
  url(/src/assets/banner_25-min.jpg);

.banner {
  background-image: $gradient, url(@/assets/banner_25-min.jpg);
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center;
  height: 37rem;
}
</style>
