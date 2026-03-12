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
      <v-btn-primary color="blue" variant="text" @click="addToPlot(datastream)"
        >Add to Current Plot</v-btn-primary
      >
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn-primary type="submit" @click="clearAndPlot(datastream)"
        >Clear and Plot</v-btn-primary
      >
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useDataVisStore } from '@/store/dataVisualization'
import hs, { Datastream, Thing } from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { ref } from 'vue'
import DatastreamInformationPanels from '@/components/Datastream/DatastreamInformationPanels.vue'
import { mdiDownload } from '@mdi/js'

defineProps({
  datastream: { type: Object as () => Datastream, required: true },
  thing: { type: Object as () => Thing, required: true },
})

const { plottedDatastreams } = storeToRefs(useDataVisStore())

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

const addToPlot = (datastream: Datastream) => {
  const index = plottedDatastreams.value.findIndex(
    (ds) => ds.id === datastream.id
  )
  if (index === -1) plottedDatastreams.value.push(datastream)
  emit('close')
}

const clearAndPlot = (datastream: Datastream) => {
  emit('close')
  plottedDatastreams.value = []
  plottedDatastreams.value.push(datastream)
}
</script>
