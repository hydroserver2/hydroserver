<template>
  <div class="data-table d-flex flex-column fill-height">
    <div class="data-table__toolbar px-4 py-2 d-flex align-center flex-wrap">
      <div class="d-flex align-center flex-shrink-0">
        <v-icon icon="mdi-table-edit" class="mr-2" color="primary" size="20" />
        <div class="d-flex flex-column">
          <span class="text-subtitle-2 font-weight-bold lh-1">
            Observations
          </span>
          <span class="text-caption text-medium-emphasis lh-1 mt-1">
            Click <b>Datetime</b> or <b>Value</b> cells to edit
          </span>
        </div>
      </div>

      <v-divider vertical class="mx-8"></v-divider>

      <div
        class="d-flex align-center justify-space-between gap-1 flex-wrap flex-grow-1"
      >
        <v-chip
          v-if="rowCount"
          size="small"
          variant="tonal"
          color="grey-darken-1"
          prepend-icon="mdi-format-list-numbered"
        >
          {{ rowCount.toLocaleString() }} row{{ rowCount === 1 ? '' : 's' }}
        </v-chip>

        <v-spacer></v-spacer>

        <v-chip
          v-if="pendingEditCount"
          size="small"
          color="warning"
          variant="tonal"
          prepend-icon="mdi-pencil-circle"
        >
          {{ pendingEditCount }} unsaved
        </v-chip>

        <v-btn
          :disabled="!pendingEditCount || isUpdating"
          variant="text"
          size="small"
          color="grey-darken-1"
          prepend-icon="mdi-undo-variant"
          @click="discardEdits"
        >
          Discard
        </v-btn>

        <v-btn
          :disabled="!pendingEditCount || isUpdating"
          :loading="isSaving"
          color="primary"
          variant="flat"
          size="small"
          prepend-icon="mdi-content-save-outline"
          @click="onSaveChanges"
        >
          Save changes
        </v-btn>
      </div>
    </div>

    <v-divider />

    <div ref="bodyEl" class="data-table__body flex-grow-1">
      <v-data-table-virtual
        :headers="headers"
        :items="virtualData"
        :height="bodyHeight"
        :item-height="ROW_HEIGHT"
        item-value="datetime"
        fixed-header
        :loading="isUpdating"
        disable-sort
        :row-props="getRowProps"
        density="compact"
      >
        <template #item.actions="{ index }">
          <v-checkbox
            color="primary"
            hide-details
            density="compact"
            :model-value="selectedData?.includes(index)"
            @update:model-value="onSelectChange($event, index)"
          />
        </template>

        <template #item.datetime="{ index }">
          <EditableCell
            :value="formatDatetimeLocal(selectedSeries?.data.dataX[index])"
            :display="formatDate(new Date(selectedSeries?.data.dataX[index]))"
            :edited="datetimeEdits.has(index)"
            :original-display="
              formatDate(new Date(selectedSeries?.data.dataX[index]))
            "
            :edited-display="
              datetimeEdits.has(index)
                ? formatDate(new Date(datetimeEdits.get(index)!))
                : ''
            "
            input-type="datetime-local"
            @save="onDatetimeSave(index, $event)"
            @clear="clearDatetimeEdit(index)"
          />
        </template>

        <template #item.value="{ index }">
          <EditableCell
            :value="String(selectedSeries?.data.dataY[index] ?? '')"
            :display="formatNumber(selectedSeries?.data.dataY[index])"
            :edited="valueEdits.has(index)"
            :original-display="formatNumber(selectedSeries?.data.dataY[index])"
            :edited-display="
              valueEdits.has(index) ? formatNumber(valueEdits.get(index)!) : ''
            "
            input-type="number"
            align="end"
            @save="onValueSave(index, $event)"
            @clear="clearValueEdit(index)"
          />
        </template>

        <template #item.qualifiers="{ index }">
          <div v-if="qualifierApplicationsAt(index).length" class="d-flex gap-1 flex-wrap">
            <v-chip
              v-for="a in qualifierApplicationsAt(index)"
              :key="a.qualifierId"
              size="x-small"
              variant="tonal"
              color="primary"
              :title="qualifierTooltip(a)"
            >
              {{ qualifierCode(a.qualifierId) }}
            </v-chip>
          </div>
        </template>
      </v-data-table-virtual>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import {
  EnumEditOperations,
  EnumFilterOperations,
  formatDate,
} from '@uwrl/qc-utils'
import { useDataSelection } from '@/composables/useDataSelection'
import { useQualifierStore } from '@/store/qualifiers'
import EditableCell from '@/components/VisualizeData/EditableCell.vue'

const { isUpdating, selectedSeries } = storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()
const { selectedData, qcDatastream } = storeToRefs(useDataVisStore())
const { clearSelected } = useDataSelection()

const qualifierStore = useQualifierStore()
const { qualifierById, applied } = storeToRefs(qualifierStore)

const isSaving = ref(false)

/**
 * `v-data-table-virtual` only virtualizes rows when it gets a concrete
 * pixel `height`. A percentage or `auto` makes it render every row in the
 * DOM, which — with a million-row dataset — turns typing a single cell
 * into a seconds-long reflow. We measure the container element and feed
 * its pixel height into the `:height` prop. `item-height` is likewise
 * required so the virtualizer can compute the visible slice from scroll
 * position without measuring each row.
 */
const ROW_HEIGHT = 40
const bodyEl = ref<HTMLDivElement | null>(null)
const bodyHeight = ref(400)
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  if (!bodyEl.value) return
  bodyHeight.value = bodyEl.value.clientHeight || 400
  resizeObserver = new ResizeObserver((entries) => {
    const h = entries[0]?.contentRect.height
    if (h && h !== bodyHeight.value) bodyHeight.value = h
  })
  resizeObserver.observe(bodyEl.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})

// Keyed by data-row index. Value edits store the new numeric y-value;
// datetime edits store the new epoch-milliseconds.
const valueEdits = reactive(new Map<number, number>())
const datetimeEdits = reactive(new Map<number, number>())

const headers = [
  { title: '', align: 'start' as const, key: 'actions', width: '50px' },
  { title: 'Datetime', align: 'start' as const, key: 'datetime' },
  { title: 'Value', align: 'end' as const, key: 'value' },
  { title: 'Qualifiers', align: 'start' as const, key: 'qualifiers' },
]

/**
 * Qualifier applications for the current QC datastream, indexed by row.
 * Read `applied` as a ref so the table re-renders as qualifiers are
 * added/removed; `qcDatastream.id` is the lookup key since qualifiers
 * are scoped to the series under active QC.
 */
const qualifierApplicationsAt = (index: number) => {
  const id = qcDatastream.value?.id
  if (!id) return []
  return applied.value[id]?.[index] ?? []
}

const qualifierCode = (qualifierId: string) =>
  qualifierById.value[qualifierId]?.code ?? ''

const qualifierTooltip = (a: {
  qualifierId: string
  appliedAt: string
  appliedBy: string
}) => {
  const q = qualifierById.value[a.qualifierId]
  if (!q) return ''
  const who = a.appliedBy ? ` — ${a.appliedBy}` : ''
  return `${q.code}: ${q.description}${who}`
}

const rowCount = computed(() => selectedSeries?.value?.data.dataX.length ?? 0)

const virtualData = computed(() => new Array(rowCount.value).fill(null))

const pendingEditCount = computed(() => valueEdits.size + datetimeEdits.size)

function onSelectChange(isSelected: boolean, index: number) {
  if (isSelected) {
    if (!selectedData.value) selectedData.value = []
    selectedData.value.push(index)
  } else {
    const pos = selectedData.value?.indexOf(index)
    if (pos !== undefined && pos >= 0) selectedData.value?.splice(pos, 1)
  }
  selectedData.value?.sort((a, b) => a - b)
}

function getRowProps(data: any) {
  const idx = data.internalItem.index
  const selected = selectedData.value?.includes(idx)
  const edited = valueEdits.has(idx) || datetimeEdits.has(idx)
  return {
    class: {
      'row--selected': selected,
      'row--edited': edited,
    },
  }
}

function formatNumber(num: unknown): string {
  if (num == null || Number.isNaN(num as number)) return ''
  return String(parseFloat((num as number).toFixed(4)))
}

/**
 * Format an epoch-ms timestamp for an <input type="datetime-local"> field:
 * `YYYY-MM-DDTHH:mm:ss` in the browser's local time zone.
 */
function formatDatetimeLocal(epoch: number | undefined): string {
  if (epoch == null || Number.isNaN(epoch)) return ''
  const d = new Date(epoch)
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  )
}

function parseDatetimeLocal(raw: string): number | null {
  if (!raw) return null
  const t = new Date(raw).getTime()
  return Number.isNaN(t) ? null : t
}

function onValueSave(index: number, raw: string) {
  const num = parseFloat(raw)
  if (Number.isNaN(num)) return
  const original = selectedSeries.value?.data.dataY[index]
  if (original != null && Math.abs(num - (original as number)) < 1e-12) {
    valueEdits.delete(index)
  } else {
    valueEdits.set(index, num)
  }
}

function clearValueEdit(index: number) {
  valueEdits.delete(index)
}

function onDatetimeSave(index: number, raw: string) {
  const epoch = parseDatetimeLocal(raw)
  if (epoch == null) return
  const original = selectedSeries.value?.data.dataX[index]
  if (original != null && epoch === original) {
    datetimeEdits.delete(index)
  } else {
    datetimeEdits.set(index, epoch)
  }
}

function clearDatetimeEdit(index: number) {
  datetimeEdits.delete(index)
}

function discardEdits() {
  valueEdits.clear()
  datetimeEdits.clear()
}

/**
 * Groups pending edits by their target (for value edits) or time delta
 * (for datetime edits) and dispatches one batched operation per group:
 *  - CHANGE_VALUES with Operator.ASSIGN for each distinct new value
 *  - SHIFT_DATETIMES with a per-group second-resolution delta
 */
async function onSaveChanges() {
  const rec = selectedSeries.value?.data
  if (!rec || pendingEditCount.value === 0) return

  isSaving.value = true
  isUpdating.value = true

  try {
    // --- Value edits: log SELECTION (indices), then ASSIGN_VALUES_BULK
    //     (values only; indices come from the prior history entry).
    if (valueEdits.size) {
      const valueIndices: number[] = []
      const valueValues: number[] = []
      for (const [idx, v] of valueEdits) {
        valueIndices.push(idx)
        valueValues.push(v)
      }
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, valueIndices],
        [EnumEditOperations.ASSIGN_VALUES_BULK, valueValues],
      ])
    }

    // --- Datetime edits: same pattern. One delete + one add under the hood.
    if (datetimeEdits.size) {
      const dtIndices: number[] = []
      const dtValues: number[] = []
      for (const [idx, newEpoch] of datetimeEdits) {
        const origEpoch = rec.dataX[idx] as number
        if (newEpoch === origEpoch) continue
        dtIndices.push(idx)
        dtValues.push(newEpoch)
      }
      if (dtIndices.length) {
        await rec.dispatch([
          [EnumFilterOperations.SELECTION, dtIndices],
          [EnumEditOperations.ASSIGN_DATETIMES_BULK, dtValues],
        ])
      }
    }

    valueEdits.clear()
    datetimeEdits.clear()
    // We just explicitly logged SELECTION + ASSIGN_*_BULK; pass
    // `recordHistory: false` so this visual clear doesn't push an
    // empty SELECTION on top.
    await clearSelected({ recordHistory: false })
    await redraw(true)
  } finally {
    isSaving.value = false
    isUpdating.value = false
  }
}
</script>

<style scoped>
.data-table__toolbar {
  background-color: rgb(var(--v-theme-surface));
  min-height: 56px;
}

.data-table__hint {
  background-color: rgba(var(--v-theme-primary), 0.04);
}

.data-table__body {
  min-height: 0;
  /* Anchor for the ResizeObserver — the v-data-table-virtual inside
     takes an explicit pixel `height` so the internal virtualizer
     actually virtualizes. Don't force child height via CSS: it fights
     the virtualizer. */
  position: relative;
}

:deep(tr.row--selected > td) {
  background-color: rgba(var(--v-theme-error), 0.06) !important;
}

:deep(tr.row--edited > td) {
  background-color: rgba(var(--v-theme-warning), 0.1) !important;
}

:deep(tr.row--selected.row--edited > td) {
  background-color: rgba(var(--v-theme-warning), 0.16) !important;
}

:deep(tbody tr:hover > td) {
  background-color: rgba(var(--v-theme-primary), 0.05) !important;
}
</style>
