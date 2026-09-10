<template>
  <v-text-field
    :model-value="selectedDatastreamLabel"
    :label="label"
    :placeholder="placeholder"
    :loading="loading"
    :disabled="disabled"
    :rules="rules"
    :density="density"
    :clearable="clearable && Boolean(modelValue)"
    :hide-details="hideDetails"
    readonly
    class="datastream-card-selector"
    @click="openSelector"
    @click:clear.stop="emit('update:modelValue', null)"
  >
    <template #append-inner>
      <v-icon :icon="mdiChevronDown" />
    </template>
  </v-text-field>

  <v-dialog v-model="selectorOpen" width="75rem">
    <DatastreamSelectorCard
      :card-title="`Select ${label.replace(/\s*\*$/, '').toLocaleLowerCase()}`"
      :datastreams="datastreams"
      :workspace-id="workspaceId"
      :monitoring-site-id="monitoringSiteId"
      @selected-datastream="selectDatastream"
      @close="selectorOpen = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Datastream, DatastreamExtended } from '@hydroserver/client'
import { mdiChevronDown } from '@mdi/js'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'
import DatastreamSelectorCard from '@/components/Datastream/DatastreamSelectorCard.vue'

type Rule = (value: any) => true | string
type Density = 'default' | 'comfortable' | 'compact'

const props = withDefaults(
  defineProps<{
    modelValue: string | null
    datastreams: Datastream[]
    label: string
    workspaceId?: string | null
    monitoringSiteId?: string | null
    placeholder?: string
    loading?: boolean
    disabled?: boolean
    rules?: Rule[]
    density?: Density
    clearable?: boolean
    hideDetails?: boolean | 'auto'
  }>(),
  {
    workspaceId: null,
    monitoringSiteId: null,
    placeholder: 'Select a datastream',
    loading: false,
    disabled: false,
    rules: () => [],
    density: 'default',
    clearable: true,
    hideDetails: false,
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: string | null): void
}>()
const selectorOpen = ref(false)

const selectedDatastream = computed(() =>
  props.datastreams.find((datastream) => datastream.id === props.modelValue)
)
const showMonitoringSiteContext = computed(
  () =>
    !props.monitoringSiteId &&
    new Set(props.datastreams.map(datastreamMonitoringSiteId).filter(Boolean))
      .size > 1
)
const selectedDatastreamLabel = computed(() => {
  const datastream = selectedDatastream.value
  if (!datastream) return ''
  const siteName = (datastream as Datastream & Record<string, any>)
    .monitoringSite?.name
  return showMonitoringSiteContext.value && siteName
    ? `${datastream.name || 'Unnamed datastream'} @ ${siteName}`
    : datastream.name || 'Unnamed datastream'
})

function openSelector() {
  if (!props.disabled) selectorOpen.value = true
}
function selectDatastream(datastream: DatastreamExtended) {
  emit('update:modelValue', datastream.id)
  selectorOpen.value = false
}
</script>

<style scoped>
.datastream-card-selector :deep(input) {
  cursor: pointer;
}
</style>
