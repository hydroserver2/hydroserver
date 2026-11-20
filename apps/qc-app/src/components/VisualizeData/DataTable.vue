<template>
  <div class="data-table d-flex flex-column fill-height">
    <div class="data-table__toolbar px-4 py-2 d-flex align-center flex-wrap">
      <div class="d-flex align-center flex-shrink-0">
        <v-icon icon="mdi-table-edit" class="mr-2" color="primary" size="20" />
        <div class="d-flex flex-column">
          <span class="text-title-small font-weight-bold lh-1">
            Observations
          </span>
          <span class="text-body-small text-medium-emphasis lh-1 mt-1">
            <template v-if="editLock === 'readOnly'">
              Committed session, read-only
            </template>
            <template v-else>
              Click <b>Datetime</b> or <b>Value</b> cells to edit
            </template>
          </span>
        </div>
      </div>

      <v-divider vertical class="mx-8"></v-divider>

      <div
        class="d-flex align-center justify-space-between ga-1 flex-wrap flex-grow-1"
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
          :disabled="!pendingEditCount || isUpdating || editLock !== null"
          :title="
            editLock === 'preview'
              ? 'Go back to the latest history step to save'
              : undefined
          "
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

    <div ref="bodyEl" class="data-table__body flex-grow-1 position-relative">
      <v-data-table-virtual
        ref="tableRef"
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
            @update:model-value="(v) => onSelectChange(v === true, index)"
          />
        </template>

        <template #item.datetime="{ index }">
          <EditableCell
            :value="formatDatetimeLocal(selectedSeries?.data.dataX[index])"
            :display="formatDateTime(selectedSeries?.data.dataX[index] as number)"
            :edited="datetimeEdits.has(index)"
            :original-display="
              formatDateTime(selectedSeries?.data.dataX[index] as number)
            "
            :edited-display="
              datetimeEdits.has(index)
                ? formatDateTime(datetimeEdits.get(index)!)
                : ''
            "
            input-type="datetime-local"
            :readonly="editLock === 'readOnly'"
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
            :readonly="editLock === 'readOnly'"
            @save="onValueSave(index, $event)"
            @clear="clearValueEdit(index)"
          />
        </template>

        <template #item.qualifiers="{ index }">
          <div v-if="qualifierApplicationsAt(index).length" class="d-flex ga-1 flex-wrap">
            <v-chip
              v-for="a in qualifierApplicationsAt(index)"
              :key="a.qualifierId"
              size="x-small"
              variant="tonal"
              color="primary"
              :title="qualifierTooltip(a)"
            >
              {{ qualifierName(a.qualifierId) }}
            </v-chip>
          </div>
        </template>
      </v-data-table-virtual>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue'

import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { EnumEditOperations, EnumFilterOperations, Snackbar } from '@uwrl/qc-utils'
import { formatDateTime } from '@/utils/time'
import { fromWallParts, wallParts } from '@/utils/timeZone'
import { useDataSelection } from '@/composables/useDataSelection'
import { QUALIFIER_TOOL_ENABLED, useQualifierStore } from '@/store/qualifiers'
import EditableCell from '@/components/VisualizeData/EditableCell.vue'
import { useEditLock } from '@/composables/useEditLock'

const { isUpdating, selectedSeries, tableScrollRequest } = storeToRefs(
  usePlotlyStore()
)
const { editLock } = useEditLock()
const { redraw } = usePlotlyStore()
const { selectedData, qcDatastream } = storeToRefs(useDataVisStore())
const { clearSelected } = useDataSelection()

const qualifierStore = useQualifierStore()
const { qualifierById, applied } = storeToRefs(qualifierStore)

const isSaving = ref(false)

// v-data-table-virtual only virtualizes when it gets a concrete pixel
// height; auto or % renders every row. Measure the container and feed
// pixels into :height. item-height lets the virtualizer compute the
// visible slice without measuring each row.
const ROW_HEIGHT = 40
const bodyEl = ref<HTMLDivElement | null>(null)
const bodyHeight = ref(400)
let resizeObserver: ResizeObserver | null = null

// v-data-table-virtual exposes scrollToIndex (offset-aware, top-aligns
// the row, and defers if the virtualizer hasn't measured yet).
const tableRef = ref<{ scrollToIndex?: (index: number) => void } | null>(null)

onMounted(() => {
  if (!bodyEl.value) return
  bodyHeight.value = bodyEl.value.clientHeight || 400
  resizeObserver = new ResizeObserver((entries) => {
    const h = entries[0]?.contentRect.height
    if (h && h !== bodyHeight.value) bodyHeight.value = h
  })
  resizeObserver.observe(bodyEl.value)
  // Honor a scroll requested while the table was unmounted (e.g. the editor
  // opened zoomed to the session window on the plot tab).
  if (tableScrollRequest.value) scrollToTime(tableScrollRequest.value.time)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})

// First index whose timestamp is at or after `time`. dataX is ascending,
// so a binary search keeps this cheap on large series.
function firstIndexAtOrAfter(time: number): number {
  const xs = selectedSeries.value?.data.dataX
  if (!xs?.length) return 0
  let lo = 0
  let hi = xs.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if ((xs[mid] as number) < time) lo = mid + 1
    else hi = mid
  }
  return lo
}

// Scroll the virtual list so the first in-range row sits at the top.
async function scrollToTime(time: number) {
  await nextTick()
  tableRef.value?.scrollToIndex?.(firstIndexAtOrAfter(time))
}

watch(
  () => tableScrollRequest.value?.seq,
  () => {
    const req = tableScrollRequest.value
    if (req) scrollToTime(req.time)
  }
)

// Keyed by row index. Values are y-numbers / epoch-ms.
const valueEdits = reactive(new Map<number, number>())
const datetimeEdits = reactive(new Map<number, number>())

// Row indices only mean the points they were staged on until the data
// changes, so any change to the record drops them rather than applying them
// to whatever point now sits at that row. Sync, so nothing reads stale rows.
watch(
  () => [selectedSeries.value?.data, selectedSeries.value?.data?.revision],
  () => {
    if (isSaving.value) return
    dropStagedEdits('because the data changed')
  },
  { flush: 'sync' }
)

// The table unmounts when the user switches tabs, taking staged edits with it.
onBeforeUnmount(() => dropStagedEdits('when the table was closed'))

function dropStagedEdits(reason: string) {
  const n = pendingEditCount.value
  if (!n) return
  discardEdits()
  Snackbar.info(`${n} unsaved table edit${n === 1 ? ' was' : 's were'} discarded ${reason}.`)
}

const headers = [
  { title: '', align: 'start' as const, key: 'actions', width: '50px' },
  { title: 'Datetime', align: 'start' as const, key: 'datetime' },
  { title: 'Value', align: 'end' as const, key: 'value' },
  ...(QUALIFIER_TOOL_ENABLED
    ? [{ title: 'Qualifiers', align: 'start' as const, key: 'qualifiers' }]
    : []),
]

const qualifierApplicationsAt = (index: number) => {
  const id = qcDatastream.value?.id
  if (!id) return []
  return applied.value[id]?.[index] ?? []
}

const qualifierName = (qualifierId: string) =>
  qualifierById.value[qualifierId]?.name ?? ''

const qualifierTooltip = (a: {
  qualifierId: string
  appliedAt: string
  appliedBy: string
}) => {
  const q = qualifierById.value[a.qualifierId]
  if (!q) return ''
  const who = a.appliedBy ? ` (${a.appliedBy})` : ''
  return `${q.name}: ${q.description}${who}`
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

// YYYY-MM-DDTHH:mm:ss in the chosen zone for <input type="datetime-local">.
function formatDatetimeLocal(epoch: number | undefined): string {
  if (epoch == null || Number.isNaN(epoch)) return ''
  const p = wallParts(epoch)
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${p.year}-${pad(p.month + 1)}-${pad(p.day)}` +
    `T${pad(p.hours)}:${pad(p.minutes)}:${pad(p.seconds)}`
  )
}

function parseDatetimeLocal(raw: string): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/.exec(raw)
  if (!m) return null
  const [, y, mo, d, h, mi, s] = m.map(Number)
  return fromWallParts(y!, mo! - 1, d!, h!, mi!, s || 0)
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

async function onSaveChanges() {
  const rec = selectedSeries.value?.data
  if (!rec || pendingEditCount.value === 0) return

  isSaving.value = true
  isUpdating.value = true

  try {
    // Log SELECTION (indices) then ASSIGN_*_BULK (values only;
    // indices are picked up from the prior history entry).
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
    // recordHistory: false because we already logged SELECTION above.
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

.data-table__body {
  min-height: 0;
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
