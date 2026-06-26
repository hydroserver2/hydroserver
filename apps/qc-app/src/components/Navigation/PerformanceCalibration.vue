<template>
  <v-menu
    v-model="open"
    :close-on-content-click="false"
    location="right"
    offset="8"
  >
    <template #activator="{ props: menuProps }">
      <v-tooltip location="right" :open-delay="400">
        <template #activator="{ props: tipProps }">
          <button
            v-if="props.railButton"
            v-bind="{ ...menuProps, ...tipProps }"
            type="button"
            class="rail-btn rail-btn-secondary"
            data-testid="calibration-button"
          >
            <span class="rail-pill rail-pill-secondary">
              <v-icon icon="mdi-speedometer" size="22" />
            </span>
            <span class="rail-label">Performance</span>
          </button>
          <v-list-item
            v-else
            v-bind="{ ...menuProps, ...tipProps }"
            prepend-icon="mdi-speedometer"
            data-testid="calibration-button"
          />
        </template>
        <span>Performance calibration</span>
      </v-tooltip>
    </template>

    <v-card max-width="440">
      <v-card-title class="text-title-medium d-flex align-center ga-2">
        <v-icon icon="mdi-speedometer" size="20" />
        Performance calibration
      </v-card-title>
      <v-divider />

      <v-card-text class="text-body-medium">
        <p class="text-medium-emphasis mb-3">
          qc-utils decides per-operation whether to spawn web workers or run
          inline on the main thread. The crossover depends on your device:
          calibration measures it once and caches the result.
        </p>

        <div class="d-flex align-center justify-space-between mb-2">
          <div>
            <div class="font-weight-medium">Last calibrated</div>
            <div class="text-body-small text-medium-emphasis">
              {{ lastCalibratedLabel }}
            </div>
          </div>
          <v-btn
            size="small"
            variant="tonal"
            color="primary"
            :loading="running"
            prepend-icon="mdi-refresh"
            @click="recalibrate"
          >
            Recalibrate
          </v-btn>
        </div>

        <v-alert
          v-if="!sabAvailable"
          type="warning"
          variant="tonal"
          density="compact"
          class="mt-2 text-body-small"
        >
          SharedArrayBuffer is unavailable in this context: all operations are
          forced inline. Enable COOP/COEP headers to restore workers.
        </v-alert>

        <template v-if="isDev">
          <v-divider class="my-3" />
          <v-expansion-panels variant="accordion" flat>
            <v-expansion-panel>
              <v-expansion-panel-title
                class="text-body-small font-weight-medium"
              >
                Benchmark details
              </v-expansion-panel-title>
              <v-expansion-panel-text class="text-body-small">
                <table class="calibration-table">
                  <tbody>
                    <tr>
                      <td>Spawn overhead</td>
                      <td class="numeric">
                        {{ fmt(profile.spawnOverheadMs, 'ms') }}
                      </td>
                    </tr>
                    <tr>
                      <td>Inline throughput</td>
                      <td class="numeric">
                        {{ fmt(profile.inlineThroughput, 'k el/ms', 1000) }}
                      </td>
                    </tr>
                    <tr>
                      <td>Worker throughput</td>
                      <td class="numeric">
                        {{ fmt(profile.workerThroughput, 'k el/ms', 1000) }}
                      </td>
                    </tr>
                    <tr>
                      <td>Hardware concurrency</td>
                      <td class="numeric">{{ profile.hwConcurrency }}</td>
                    </tr>
                    <tr>
                      <td>SharedArrayBuffer</td>
                      <td class="numeric">{{ sabAvailable ? 'yes' : 'no' }}</td>
                    </tr>
                  </tbody>
                </table>

                <div v-if="detail" class="mt-2">
                  <div class="font-weight-medium mb-1">Raw samples (ms)</div>
                  <table class="calibration-table">
                    <tbody>
                      <tr>
                        <td>Spawn roundtrip</td>
                        <td class="numeric">
                          {{ fmtSamples(detail.samples.spawnRoundtripMs) }}
                        </td>
                      </tr>
                      <tr>
                        <td>Inline scan</td>
                        <td class="numeric">
                          {{ fmtSamples(detail.samples.inlineScanMs) }}
                        </td>
                      </tr>
                      <tr>
                        <td>Worker scan</td>
                        <td class="numeric">
                          {{ fmtSamples(detail.samples.workerScanMs) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <v-expansion-panel>
              <v-expansion-panel-title
                class="text-body-small font-weight-medium"
              >
                Operation table
              </v-expansion-panel-title>
              <v-expansion-panel-text class="text-body-small">
                <p class="text-medium-emphasis mb-2">
                  Weight is the operation's relative per-element cost against
                  the reference
                  <code>VALUE_THRESHOLD</code> scan (weight 1.0). It describes
                  the algorithm, not the machine, so it's shipped with qc-utils,
                  not measured at runtime. Recalibration only re-measures the
                  three device primitives above; weights stay fixed. The
                  dispatch formula is <code>weight Ã— N / throughput</code>, so
                  one universal weight per op plus your per-device throughputs
                  covers the full operation catalog.
                </p>
                <table class="calibration-table op-table">
                  <thead>
                    <tr>
                      <th>Operation</th>
                      <th>Mode</th>
                      <th class="numeric">Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in opTable" :key="row.op">
                      <td>{{ row.op }}</td>
                      <td>
                        <v-chip
                          :color="
                            row.mode === 'calibrated'
                              ? 'primary'
                              : row.mode === 'always-inline'
                                ? 'success'
                                : 'default'
                          "
                          size="x-small"
                          variant="tonal"
                        >
                          {{ row.mode }}
                        </v-chip>
                      </td>
                      <td class="numeric">{{ row.weight.toFixed(1) }}</td>
                    </tr>
                  </tbody>
                </table>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </template>
      </v-card-text>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  ensureCalibration,
  getCalibration,
  getLastBenchmarkDetail,
  getOperationTable,
  onCalibrationChange,
  type BenchmarkDetail,
  type DeviceProfile,
} from '@uwrl/qc-utils'

const props = withDefaults(defineProps<{ railButton?: boolean }>(), {
  railButton: false,
})

const isDev = import.meta.env.DEV
const open = ref(false)
const running = ref(false)
const profile = ref<DeviceProfile>(getCalibration())
const detail = ref<BenchmarkDetail | null>(getLastBenchmarkDetail())

const sabAvailable = typeof SharedArrayBuffer !== 'undefined'
const opTable = computed(() => getOperationTable())

const lastCalibratedLabel = computed(() => {
  if (!profile.value.measuredAt) return 'Never (using defaults)'
  const diffMs = Date.now() - profile.value.measuredAt
  if (diffMs < 60_000) return 'Just now'
  const minutes = Math.round(diffMs / 60_000)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 48) return `${hours} hr ago`
  const days = Math.round(hours / 24)
  return `${days} days ago`
})

async function recalibrate() {
  running.value = true
  try {
    await ensureCalibration({ force: true })
    profile.value = getCalibration()
    detail.value = getLastBenchmarkDetail()
  } finally {
    running.value = false
  }
}

let unsubscribe: (() => void) | null = null

onMounted(() => {
  unsubscribe = onCalibrationChange((p) => {
    profile.value = { ...p }
    detail.value = getLastBenchmarkDetail()
  })
})

onBeforeUnmount(() => {
  unsubscribe?.()
})

function fmt(value: number, unit: string, scale = 1): string {
  if (!Number.isFinite(value) || value === 0) return 'n/a'
  return `${(value / scale).toFixed(2)} ${unit}`
}

function fmtSamples(arr: number[] | undefined): string {
  if (!arr?.length) return 'n/a'
  return arr.map((x) => x.toFixed(1)).join(', ')
}
</script>

<style scoped>
.calibration-table {
  width: 100%;
  border-collapse: collapse;
}

.calibration-table td,
.calibration-table th {
  padding: 2px 4px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  vertical-align: middle;
}

.calibration-table th {
  text-align: left;
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-weight: 600;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.rail-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  width: 100%;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
}

.rail-btn:hover .rail-pill {
  background: rgba(0, 0, 0, 0.05);
}

.rail-pill {
  width: 58px;
  height: 32px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background 0.15s;
}

.rail-btn-secondary {
  color: #5f6368;
}

.rail-btn-secondary:hover .rail-pill-secondary {
  background: rgba(21, 101, 192, 0.08);
}

.rail-pill-secondary {
  background: transparent;
}

.rail-label {
  font-size: 10.5px;
  color: #49454f;
  line-height: 1.2;
  text-align: center;
}

.calibration-table td.numeric,
.calibration-table th.numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.op-table td:first-child {
  font-family: monospace;
  font-size: 0.75rem;
}
</style>
