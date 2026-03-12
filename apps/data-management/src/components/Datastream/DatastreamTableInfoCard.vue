<template>
  <v-card>
    <v-toolbar flat color="blue-darken-2">
      <v-card-title> Datastream information </v-card-title>
      <v-spacer />
      <v-btn
        :loading="downloading"
        :prepend-icon="mdiDownload"
        color="blue-lighten-5"
        @click="downloadDatastream(datastream.id)"
        >Download</v-btn
      >
    </v-toolbar>

    <DatastreamInformationPanels :datastream-id="datastream.id" />

    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { Datastream, Thing } from '@hydroserver/client'
import { ref } from 'vue'
import DatastreamInformationPanels from '@/components/Datastream/DatastreamInformationPanels.vue'
import hs from '@hydroserver/client'
import { mdiDownload } from '@mdi/js'

defineProps({
  datastream: { type: Object as () => Datastream, required: true },
  thing: { type: Object as () => Thing, required: true },
})

const emit = defineEmits(['close'])

const downloading = ref(false)

const downloadDatastream = async (id: string) => {
  downloading.value = true
  try {
    await hs.datastreams.downloadCsv(id)
  } catch (error) {
    console.error('Error downloading datastream', error)
  }
  downloading.value = false
}
</script>
