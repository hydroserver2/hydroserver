<template>
  <v-card class="datastream-information-card">
    <v-toolbar flat color="surface-subtle">
      <v-card-title> Datastream information </v-card-title>
      <v-spacer />
      <v-btn
        :loading="downloading"
        :prepend-icon="mdiDownload"
        color="primary"
        variant="tonal"
        data-testid="download-datastream-csv"
        @click="downloadDatastream(datastream.id)"
        >Download</v-btn
      >
    </v-toolbar>

    <DatastreamInformationPanels :datastream-id="datastream.id" />

    <v-card-actions>
      <v-btn-dialog-action
        variant="text"
        data-testid="add-datastream-to-plot"
        @click="addToPlot(datastream)"
        >Add to Current Plot</v-btn-dialog-action
      >
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn-dialog-action
        type="submit"
        data-testid="clear-and-plot-datastream"
        @click="clearAndPlot(datastream)"
        >Clear and Plot</v-btn-dialog-action
      >
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useDataVisStore } from '@/store/dataVisualization'
import { Datastream, MonitoringSite } from '@hydroserver/client'
import { downloadDatastreamCsv } from '@/utils/csvExport'
import { storeToRefs } from 'pinia'
import { ref } from 'vue'
import DatastreamInformationPanels from '@/components/Datastream/DatastreamInformationPanels.vue'
import { mdiDownload } from '@mdi/js'

defineProps({
  datastream: { type: Object as () => Datastream, required: true },
  monitoringSite: { type: Object as () => MonitoringSite, required: true },
})

const { plottedDatastreams } = storeToRefs(useDataVisStore())

const emit = defineEmits(['close'])

const downloading = ref(false)

const downloadDatastream = async (id: string) => {
  downloading.value = true
  try {
    await downloadDatastreamCsv(id)
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
