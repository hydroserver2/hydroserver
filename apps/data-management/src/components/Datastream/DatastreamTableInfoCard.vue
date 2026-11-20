<template>
  <v-card class="datastream-details-card d-flex flex-column">
    <v-toolbar flat color="primary" density="comfortable" class="shrink-0">
      <v-card-title class="hs-text-md"> Datastream information </v-card-title>
      <v-spacer />
      <v-btn
        :loading="downloading"
        :prepend-icon="mdiDownload"
        color="on-primary"
        variant="tonal"
        @click="downloadDatastream(datastream.id)"
        >Download</v-btn
      >
    </v-toolbar>

    <div class="datastream-details-content grow overflow-y-auto">
      <DatastreamInformationPanels :datastream-id="datastream.id" />
    </div>

    <v-card-actions class="datastream-details-actions shrink-0">
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { Datastream, MonitoringSite } from '@hydroserver/client'
import { ref } from 'vue'
import DatastreamInformationPanels from '@/components/Datastream/DatastreamInformationPanels.vue'
import { downloadDatastreamCsv } from '@/utils/csvExport'
import { mdiDownload } from '@mdi/js'

defineProps({
  datastream: { type: Object as () => Datastream, required: true },
  monitoringSite: { type: Object as () => MonitoringSite, required: true },
})

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
</script>

<style scoped>
.datastream-details-card {
  max-height: 90vh;
  overflow: hidden;
}

.datastream-details-content {
  min-height: 0;
}

.datastream-details-actions {
  background: var(--hs-surface);
  border-top: 1px solid var(--hs-border);
}
</style>
