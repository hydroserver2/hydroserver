<template>
  <v-card v-if="loaded">
    <v-toolbar color="red-darken-4">
      <v-card-title class="text-h5">
        <v-icon :icon="mdiAlert" />
        {{
          hasDatastreams
            ? `Cannot delete ${itemName}`
            : `Confirm ${itemName} deletion`
        }}
      </v-card-title>
    </v-toolbar>

    <v-card-text v-if="hasDatastreams">
      This {{ itemName }} cannot be deleted because it's being referenced by
      some of your datastreams. Before deletion, all of the following
      datastreams need to be deleted or use a different {{ itemName }}:
      <div class="my-4" v-for="ds in datastreams">
        <router-link :to="`/sites/${ds.thingId}`">
          {{ ds.name }}
        </router-link>
      </div>
    </v-card-text>
    <v-card-text v-else>
      This {{ itemName }} isn't being used by any datastreams and is safe to
      delete.
    </v-card-text>

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn-cancel @click="emit('close')">Cancel</v-btn-cancel>
      <v-btn-delete v-if="!hasDatastreams" @click="onDelete"
        >Delete</v-btn-delete
      >
    </v-card-actions>
  </v-card>
  <v-card v-else>
    <FullScreenLoader :loading-text="'Fetching datastreams...'" />
  </v-card>
</template>

<script setup lang="ts">
import hs, { Datastream } from '@hydroserver/client'
import { computed, onMounted, ref } from 'vue'
import FullScreenLoader from '../base/FullScreenLoader.vue'
import { mdiAlert } from '@mdi/js'

const datastreams = ref<Datastream[]>([])
const loaded = ref(false)

type DatastreamFilterKey =
  | 'unit_id'
  | 'sensor_id'
  | 'observed_property_id'
  | 'processing_level_id'
  | 'result_qualifier_id'

const emit = defineEmits(['delete', 'close'])
const props = defineProps<{
  itemName: String
  itemID: String
  parameterName: DatastreamFilterKey
  workspaceId?: String
}>()

const onDelete = () => {
  emit('delete')
  emit('close')
}

const hasDatastreams = computed(() => datastreams.value?.length > 0)

onMounted(async () => {
  try {
    const filter = {
      [props.parameterName]: [props.itemID],
    } as Partial<Record<DatastreamFilterKey, string[]>>

    datastreams.value = await hs.datastreams.listAllItems(filter)
    loaded.value = true
  } catch (error) {
    console.error('Error fetching things', error)
  }
})
</script>
