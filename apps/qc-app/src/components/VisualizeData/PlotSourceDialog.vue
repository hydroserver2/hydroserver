<template>
  <v-card rounded="lg" data-testid="plot-source-dialog">
    <div class="px-4 pt-4 pb-2">
      <div class="text-title-medium font-weight-bold">
        Plot "{{ source.name }}"
      </div>
      <div class="text-body-small text-medium-emphasis mt-1">
        This datastream has quality-controlled versions. Pick which series to
        plot.
      </div>
    </div>

    <v-divider />

    <div class="plot-source__body pa-4">
      <div v-if="loading" class="py-6 text-center">
        <v-progress-circular indeterminate color="primary" size="28" />
      </div>

      <template v-else>
        <v-card
          v-for="row in rows"
          :key="row.id"
          variant="outlined"
          class="mb-2"
          :class="{ 'plot-source__row--disabled': isDisabled(row.id) }"
        >
          <v-checkbox
            :model-value="checked.includes(row.id)"
            :disabled="isDisabled(row.id)"
            density="compact"
            hide-details
            color="primary"
            class="px-2"
            :data-testid="`plot-option-${row.id}`"
            @update:model-value="toggle(row.id)"
          >
            <template #label>
              <div class="d-flex align-center ga-2" style="min-width: 0">
                <v-icon
                  :icon="row.raw ? 'mdi-chart-line' : 'mdi-pencil-box-outline'"
                  :color="row.raw ? undefined : 'primary'"
                  size="18"
                />
                <div class="d-flex flex-column" style="min-width: 0">
                  <span class="text-body-medium font-weight-medium">
                    {{ row.name }}
                  </span>
                  <span class="text-body-small text-medium-emphasis">
                    {{ row.summary }}
                  </span>
                </div>
              </div>
            </template>
          </v-checkbox>
        </v-card>

        <div
          v-if="!slotsLeftForNew"
          class="text-body-small text-medium-emphasis"
          data-testid="plot-source-cap"
        >
          Maximum of 4 datastreams plotted; remove one to add another.
        </div>
      </template>
    </div>

    <v-divider />

    <v-card-actions class="px-4 py-2">
      <v-spacer />
      <v-btn variant="text" data-testid="plot-source-cancel" @click="emit('cancel')">
        Cancel
      </v-btn>
      <v-btn
        color="primary"
        variant="flat"
        data-testid="plot-source-apply"
        @click="emit('apply', checked)"
      >
        Apply
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Datastream, DatastreamExtended } from '@hydroserver/client'
import type { ManagedDatastreamOption } from '@/composables/useManagedDatastreams'
import { datastreamSummary } from '@/utils/datastreamSummary'

const props = defineProps<{
  source: Datastream & Partial<DatastreamExtended>
  options: ManagedDatastreamOption[]
  plottedIds: string[]
  loading?: boolean
  /** Free slots under the 4-datastream plot cap, ignoring this source's group. */
  slotsLeft: number
}>()

const emit = defineEmits<{
  (e: 'apply', ids: string[]): void
  (e: 'cancel'): void
}>()

const checked = ref<string[]>([...props.plottedIds])

// The dialog is reopened to edit an existing selection, so re-seed whenever
// the caller hands over a different one.
watch(
  () => props.plottedIds,
  (ids) => {
    checked.value = [...ids]
  }
)

interface Row {
  id: string
  name: string
  summary: string
  raw: boolean
}

// Raw first so the first-plotted-wins QC rule keeps the source as target
// when both it and a managed datastream are picked from an empty plot.
const rows = computed<Row[]>(() => [
  {
    id: props.source.id,
    name: 'Raw data',
    summary: datastreamSummary(props.source),
    raw: true,
  },
  ...props.options.map((o) => ({
    id: o.managed.id,
    name: o.managed.name,
    summary: datastreamSummary(o.managed, o.sessions),
    raw: false,
  })),
])

const slotsLeftForNew = computed(() => props.slotsLeft - checked.value.length)

const isDisabled = (id: string) =>
  !checked.value.includes(id) && slotsLeftForNew.value <= 0

function toggle(id: string) {
  if (checked.value.includes(id)) {
    checked.value = checked.value.filter((x) => x !== id)
    return
  }
  if (isDisabled(id)) return
  // Re-derive from `rows` so the applied order is always display order,
  // not the order the boxes happened to be clicked.
  const wanted = new Set([...checked.value, id])
  checked.value = rows.value.map((r) => r.id).filter((rid) => wanted.has(rid))
}
</script>

<style scoped>
.plot-source__body {
  max-height: 60vh;
  overflow-y: auto;
}

.plot-source__row--disabled {
  opacity: 0.5;
}

/* Vuetify sizes the label to its content and dims it. Neither suits a row
   whose label carries the name and summary. */
.plot-source__body :deep(.v-selection-control .v-label) {
  width: 100%;
  opacity: 1;
}

.plot-source__body :deep(.v-label > div) {
  min-width: 0;
}

.plot-source__body :deep(.v-label span) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
