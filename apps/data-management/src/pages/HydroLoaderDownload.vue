<template>
  <v-container>
    <v-row class="mb-4">
      <v-col cols="auto">
        <h5 class="text-h5">Download Streaming Data Loader</h5>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-btn
          size="large"
          variant="elevated"
          :prepend-icon="mdiApple"
          :href="macosLink"
        >
          Download for MacOS
        </v-btn>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-btn
          size="large"
          variant="elevated"
          :prepend-icon="mdiMicrosoftWindows"
          :href="windowsLink"
        >
          Download for Windows
        </v-btn>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-btn
          size="large"
          variant="elevated"
          :prepend-icon="mdiUbuntu"
          :href="ubuntuLink"
        >
          Download for Ubuntu
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { mdiApple, mdiMicrosoftWindows, mdiUbuntu } from '@mdi/js'

let version = 'v1.8.0' // TODO: Add this as an environment variable
let macosLink = `https://github.com/hydroserver2/streaming-data-loader/releases/download/${version}/Streaming.Data.Loader.MacOS.dmg`
let windowsLink = `https://github.com/hydroserver2/streaming-data-loader/releases/download/${version}/Streaming.Data.Loader.Windows.zip`
let ubuntuLink = `https://github.com/hydroserver2/streaming-data-loader/releases/download/${version}/Streaming.Data.Loader.Ubuntu.zip`
</script>

<style scoped></style>
