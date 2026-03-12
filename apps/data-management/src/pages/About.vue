<template>
  <v-container v-if="settings.aboutInformation.showAboutInformation">
    <h4 class="text-h4 my-6">
      {{ settings.aboutInformation.title  || 'About us' }}
    </h4>
    <p class="mb-4">
      {{ settings.aboutInformation.text }}
    </p>
    <AboutCards :cards="cards" :num-cols="4" />
  </v-container>
  <AboutHydroServer />
</template>

<script setup lang="ts">
import AboutCards, { Card } from '@/components/About/AboutCards.vue'
import AboutHydroServer from '@/components/About/AboutHydroServer.vue'
import { settings } from '@/config/settings'

const cards = settings.aboutInformation.contactOptions.map(contactOption => ({
  title: contactOption.title,
  titleIcon: contactOption.icon,
  text: contactOption.text,
  btnText: contactOption.action,
  btnColor: 'primary',
  btnHref: contactOption.link,
})) as Card[]
</script>
