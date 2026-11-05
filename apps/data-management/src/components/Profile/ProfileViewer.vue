<template>
  <section
    class="profile-viewer"
    :aria-label="`${datastream.name} profile viewer`"
    :aria-busy="loading"
  >
    <header class="profile-header">
      <h2 class="hs-subheading">{{ datastream.name }}</h2>
      <v-btn
        v-if="!syncRoute"
        variant="text"
        size="small"
        :to="visualizationLink"
        >Visualize data page <v-icon :icon="mdiArrowRight" end
      /></v-btn>
    </header>
    <v-progress-linear
      v-if="loading"
      color="primary"
      indeterminate
      aria-label="Loading profiles"
    />
    <v-alert v-else-if="error" type="error" variant="tonal" class="ma-4">
      {{ error }} <v-btn variant="text" @click="load">Retry</v-btn>
    </v-alert>
    <HsEmptyState
      v-else-if="!data?.visits.length"
      title="No profile visits available"
      compact
    />
    <div v-else class="profile-body">
      <div class="profile-chart-panel">
        <div
          ref="plotElement"
          v-show="traces.length"
          class="profile-chart"
          role="img"
          :aria-label="chartDescription"
        />
        <HsEmptyState
          v-if="!traces.length"
          title="Choose visits to compare"
          compact
        />
      </div>
      <aside class="profile-controls">
        <v-tabs
          v-model="mode"
          color="primary"
          grow
          density="compact"
          aria-label="Profile comparison"
        >
          <v-tab value="visits">Compare visits</v-tab>
          <v-tab value="analytes">Compare analytes</v-tab>
        </v-tabs>
        <div class="profile-controls-content">
          <template v-if="mode === 'visits'">
            <v-checkbox
              v-for="(visit, index) in data.visits"
              :key="visit.phenomenonTime"
              v-model="selectedVisits"
              :value="visit.phenomenonTime"
              :label="visit.label"
              hide-details
              density="compact"
              :color="index === 0 ? 'primary' : 'default'"
            >
              <template #label>
                <span class="profile-option-label hs-text-sm">
                  <span>{{ visit.label }}</span>
                  <v-chip
                    size="x-small"
                    :color="statusColor(visit.status)"
                    variant="tonal"
                    >{{ visit.status }}</v-chip
                  >
                </span>
              </template>
            </v-checkbox>
          </template>
          <template v-else>
            <v-select
              v-model="selectedVisit"
              :items="data.visits"
              item-title="label"
              item-value="phenomenonTime"
              label="Visit"
              hide-details
              class="mb-4"
            />
            <v-checkbox
              v-for="analyte in otherAnalytes"
              :key="analyte.datastreamId"
              :model-value="companion === analyte.datastreamId"
              :disabled="
                !available(analyte.datastreamId) ||
                Boolean(companion && companion !== analyte.datastreamId)
              "
              :label="analyte.name"
              :title="
                companion &&
                companion !== analyte.datastreamId &&
                available(analyte.datastreamId)
                  ? 'Remove the selected analyte to compare another'
                  : undefined
              "
              hide-details
              density="compact"
              color="warning"
              @update:model-value="
                companion = $event ? analyte.datastreamId : ''
              "
            >
              <template #label>
                <span class="profile-option-label hs-text-sm">
                  <span
                    >{{ analyte.name }}
                    <span class="text-medium-emphasis"
                      >({{ analyte.unit }})</span
                    ></span
                  >
                  <span
                    v-if="!available(analyte.datastreamId)"
                    class="text-medium-emphasis"
                    >No shared visit</span
                  >
                </span>
              </template>
            </v-checkbox>
          </template>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Datastream } from '@hydroserver/client'
import { HsEmptyState } from '@hydroserver/design-system/vue'
import { mdiArrowRight } from '@mdi/js'
import { fetchProfileData } from '@/services/profiles'
import {
  hasProfileValues,
  profilePoints,
  type ProfileData,
} from '@/models/profile'

const props = defineProps<{ datastream: Datastream; syncRoute?: boolean }>()
const route = useRoute(),
  router = useRouter()
const data = ref<ProfileData | null>(null),
  loading = ref(false),
  error = ref('')
const mode = ref<'visits' | 'analytes'>('visits')
const selectedVisits = ref<string[]>([]),
  selectedVisit = ref(''),
  companion = ref('')
const plotElement = ref<HTMLElement | null>(null)
let abort: AbortController | undefined,
  generation = 0,
  disposed = false
let plotly: any, observer: ResizeObserver | undefined
const primaryAnalyte = computed(() =>
  data.value?.analytes.find((item) => item.datastreamId === props.datastream.id)
)
const otherAnalytes = computed(
  () =>
    data.value?.analytes.filter(
      (item) => item.datastreamId !== props.datastream.id
    ) ?? []
)
const available = (id: string) =>
  Boolean(data.value && hasProfileValues(data.value, id, selectedVisit.value))
const statusColor = (status: string) =>
  status === 'lab confirmed'
    ? 'success'
    : status === 'lab pending'
      ? 'warning'
      : 'default'
const selectionQuery = computed(() => ({
  profileMode: mode.value,
  profileVisits: selectedVisits.value.join(','),
  profileVisit: selectedVisit.value,
  profileAnalyte: companion.value || undefined,
}))
const visualizationLink = computed(() => ({
  name: 'VisualizeData',
  query: {
    sites: props.datastream.monitoringSiteId,
    datastreams: props.datastream.id,
    ...selectionQuery.value,
  },
}))
const chartDescription = computed(
  () =>
    `${primaryAnalyte.value?.name ?? props.datastream.name} against ${data.value?.zReference ?? 'vertical coordinate'} in ${data.value?.zUnit ?? 'm'}. ${mode.value === 'visits' ? selectedVisits.value.length + ' visits selected' : 'Visit ' + selectedVisit.value}`
)
const traces = computed(() => {
  if (!data.value) return []
  const selections =
    mode.value === 'visits'
      ? data.value.visits
          .filter((visit) =>
            selectedVisits.value.includes(visit.phenomenonTime)
          )
          .map((visit) => ({
            id: props.datastream.id,
            time: visit.phenomenonTime,
            name: visit.label,
            unit: primaryAnalyte.value?.unit ?? '',
          }))
      : [props.datastream.id, companion.value].filter(Boolean).map((id) => ({
          id,
          time: selectedVisit.value,
          name:
            data.value!.analytes.find((item) => item.datastreamId === id)
              ?.name ?? id,
          unit:
            data.value!.analytes.find((item) => item.datastreamId === id)
              ?.unit ?? '',
        }))
  return selections.map((selection, index) => {
    const points = profilePoints(data.value!, selection.id, selection.time)
    return {
      type: 'scatter',
      mode: 'lines+markers',
      name: selection.name,
      x: points.map((point) => point.result),
      y: points.map((point) => point.z),
      connectgaps: false,
      xaxis: mode.value === 'analytes' && index === 1 ? 'x2' : 'x',
      line: {
        color: color(index),
        width: 2,
        dash:
          index === 0 ? 'solid' : ['dash', 'dot', 'dashdot'][(index - 1) % 3],
      },
      marker: { size: 5 },
      hovertemplate: `%{x} ${selection.unit}<br>%{y} ${data.value!.zUnit}<extra>%{fullData.name}</extra>`,
    }
  })
})
function color(index: number) {
  const role =
    mode.value === 'analytes' && index === 1
      ? '--hs-warning'
      : ['--hs-primary', '--hs-default', '--hs-info', '--hs-secondary'][
          index % 4
        ]
  return getComputedStyle(document.documentElement)
    .getPropertyValue(role)
    .trim()
}
async function load() {
  abort?.abort()
  abort = new AbortController()
  const version = ++generation
  loading.value = true
  error.value = ''
  data.value = null
  try {
    const result = await fetchProfileData(props.datastream.id, abort.signal)
    if (disposed || version !== generation) return
    result.visits.sort((a, b) =>
      b.phenomenonTime.localeCompare(a.phenomenonTime)
    )
    data.value = result
    const times = new Set(result.visits.map((item) => item.phenomenonTime))
    mode.value =
      props.syncRoute && route.query.profileMode === 'analytes'
        ? 'analytes'
        : 'visits'
    const requestedVisits =
      props.syncRoute && typeof route.query.profileVisits === 'string'
        ? route.query.profileVisits.split(',')
        : []
    selectedVisits.value = requestedVisits.filter((time) => times.has(time))
    if (
      !selectedVisits.value.length &&
      !(props.syncRoute && route.query.profileVisits === '')
    )
      selectedVisits.value = result.visits
        .slice(0, 1)
        .map((item) => item.phenomenonTime)
    selectedVisit.value =
      props.syncRoute &&
      typeof route.query.profileVisit === 'string' &&
      times.has(route.query.profileVisit)
        ? route.query.profileVisit
        : (result.visits[0]?.phenomenonTime ?? '')
    companion.value =
      props.syncRoute &&
      typeof route.query.profileAnalyte === 'string' &&
      otherAnalytes.value.some(
        (item) => item.datastreamId === route.query.profileAnalyte
      ) &&
      available(route.query.profileAnalyte)
        ? route.query.profileAnalyte
        : ''
  } catch (cause) {
    if (version === generation && !disposed && !abort.signal.aborted)
      error.value =
        cause instanceof Error ? cause.message : 'Unable to load profiles.'
  } finally {
    if (version === generation && !disposed) loading.value = false
  }
}
watch(selectedVisit, () => {
  if (companion.value && !available(companion.value)) companion.value = ''
})
watch(() => props.datastream.id, load, { immediate: true })
watch(selectionQuery, (query) => {
  if (props.syncRoute && !loading.value && data.value)
    void router.replace({ query: { ...route.query, ...query } })
})
let renderVersion = 0
watch(
  [traces, loading, plotElement],
  async () => {
    const version = ++renderVersion
    await nextTick()
    const element = plotElement.value
    if (!element || loading.value || !traces.value.length) return
    try {
      if (!plotly) {
        const module = await import('plotly.js-dist')
        plotly = module.default ?? module
      }
      if (
        disposed ||
        version !== renderVersion ||
        element !== plotElement.value
      )
        return
      const css = getComputedStyle(document.documentElement)
      const token = (name: string) => css.getPropertyValue(name).trim()
      await plotly.react(
        element,
        traces.value,
        {
          autosize: true,
          margin: {
            l: 76,
            r: 24,
            t: mode.value === 'analytes' && companion.value ? 62 : 24,
            b: 110,
          },
          font: {
            family: token('--hs-font-body'),
            color: token('--hs-text-secondary'),
            size: 12,
          },
          paper_bgcolor: token('--hs-surface'),
          plot_bgcolor: token('--hs-surface'),
          xaxis: {
            title: {
              text: `${primaryAnalyte.value?.name ?? ''} (${primaryAnalyte.value?.unit ?? ''})`,
            },
            zeroline: false,
            gridcolor: token('--hs-border'),
            color: token('--hs-primary'),
          },
          xaxis2: {
            overlaying: 'x',
            side: 'top',
            title: {
              text: `${otherAnalytes.value.find((item) => item.datastreamId === companion.value)?.name ?? ''} (${otherAnalytes.value.find((item) => item.datastreamId === companion.value)?.unit ?? ''})`,
            },
            showgrid: false,
            color: token('--hs-warning'),
            zeroline: false,
          },
          yaxis: {
            title: { text: `${data.value?.zReference} (${data.value?.zUnit})` },
            autorange:
              data.value?.positiveDirection === 'down' ? 'reversed' : true,
            gridcolor: token('--hs-border'),
            zeroline: false,
          },
          legend: { orientation: 'h', y: -0.4, yanchor: 'top', x: 0 },
          showlegend: true,
        },
        {
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['lasso2d', 'select2d'],
          toImageButtonOptions: { filename: 'reservoir-profile' },
        }
      )
    } catch {
      if (!disposed && version === renderVersion)
        error.value = 'Unable to draw the profile. Please retry.'
    }
  },
  { flush: 'post' }
)
watch(plotElement, (element, previous) => {
  observer?.disconnect()
  if (previous && plotly) plotly.purge(previous)
  if (element) {
    observer = new ResizeObserver(() => {
      if (
        plotly &&
        element.isConnected &&
        element.clientHeight &&
        element.clientWidth
      )
        void plotly.Plots.resize(element).catch(() => {})
    })
    observer.observe(element)
  }
})
onBeforeUnmount(() => {
  disposed = true
  abort?.abort()
  observer?.disconnect()
  if (plotly && plotElement.value) plotly.purge(plotElement.value)
})
</script>

<style scoped>
.profile-viewer {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--hs-surface);
  border-radius: var(--hs-radius-md);
  overflow: auto;
}
.profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--hs-space-8);
  padding: var(--hs-space-12) var(--hs-space-16);
  border-bottom: 1px solid var(--hs-border);
}
.profile-header h2 {
  margin: 0;
}
.profile-body {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
  flex: 1;
  min-height: 0;
}
.profile-chart-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.profile-chart {
  flex: 1;
  min-height: 340px;
  width: 100%;
}
.profile-controls {
  min-width: 0;
  border-left: 1px solid var(--hs-border);
  overflow: auto;
}
.profile-controls-content {
  padding: var(--hs-space-16);
}
.profile-option-label {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--hs-space-4) var(--hs-space-8);
  white-space: normal;
  padding-block: var(--hs-space-4);
}
@media (max-width: 800px) {
  .profile-body {
    grid-template-columns: minmax(0, 1fr);
    flex: none;
    min-height: auto;
  }
  .profile-controls {
    min-width: 0;
    border-left: 0;
    border-top: 1px solid var(--hs-border);
    overflow: visible;
  }
  .profile-chart {
    flex: none;
    height: 340px;
  }
}
</style>
