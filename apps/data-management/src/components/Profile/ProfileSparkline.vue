<template>
  <div class="profile-preview">
    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
      aria-label="Loading latest profile"
    />
    <button
      v-else-if="hasValues"
      type="button"
      class="profile-preview-button"
      :aria-label="`Open latest profile for ${datastream.name}`"
      @click="$emit('openChart')"
    >
      <svg
        viewBox="0 0 80 64"
        role="img"
        aria-label="Latest vertical profile"
        preserveAspectRatio="xMidYMid meet"
      >
        <path :d="area" class="profile-preview-area" />
        <path d="M4 4 V60 H76" class="profile-preview-axis" />
        <path :d="line" class="profile-preview-line" />
      </svg>
    </button>
    <span v-else class="hs-text-sm text-medium-emphasis"
      >{{ error ? 'Preview unavailable' : 'No profile measurements'
      }}<v-btn v-if="error" size="x-small" variant="text" @click="load"
        >Retry</v-btn
      ></span
    >
    <span v-if="hasValues" class="hs-text-sm text-medium-emphasis"
      >Latest <strong>{{ visitLabel }}</strong></span
    >
  </div>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { Datastream } from '@hydroserver/client'
import { fetchProfileData } from '@/services/profiles'
import { profilePoints, type ProfileData } from '@/models/profile'
const props = defineProps<{ datastream: Datastream }>()
defineEmits<{ openChart: [] }>()
const data = ref<ProfileData | null>(null),
  loading = ref(false),
  error = ref(false)
let controller: AbortController | undefined
const latest = computed(
  () =>
    data.value?.visits
      .slice()
      .sort((a, b) => b.phenomenonTime.localeCompare(a.phenomenonTime))[0]
)
const visitLabel = computed(() => latest.value?.label)
const points = computed(() =>
  data.value && latest.value
    ? profilePoints(
        data.value,
        props.datastream.id,
        latest.value.phenomenonTime
      )
    : []
)
const hasValues = computed(() =>
  points.value.some((point) => point.result !== null)
)
const paths = computed(() => {
  const valid = points.value.filter((point) => point.result !== null)
  if (!valid.length) return { line: '', area: '' }
  const min = Math.min(...valid.map((point) => point.result!)),
    max = Math.max(...valid.map((point) => point.result!))
  const low = Math.min(...valid.map((point) => point.z)),
    high = Math.max(...valid.map((point) => point.z))
  const x = (value: number) =>
    8 + (max === min ? 0.5 : (value - min) / (max - min)) * 64
  const y = (z: number) =>
    4 +
    (data.value?.positiveDirection === 'up'
      ? 1 - (z - low) / (high - low || 1)
      : (z - low) / (high - low || 1)) *
      56
  let line = '',
    area = '',
    segment: typeof valid = []
  const flush = () => {
    if (!segment.length) return
    const path = segment
      .map(
        (point, index) =>
          `${index ? 'L' : 'M'}${x(point.result!)} ${y(point.z)}`
      )
      .join(' ')
    line += path
    area += `${path} L4 ${y(segment.at(-1)!.z)} L4 ${y(segment[0].z)} Z `
    segment = []
  }
  for (const point of points.value) {
    if (point.result === null) flush()
    else segment.push(point)
  }
  flush()
  return { line, area }
})
const line = computed(() => paths.value.line),
  area = computed(() => paths.value.area)
async function load() {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  error.value = false
  data.value = null
  try {
    const result = await fetchProfileData(props.datastream.id, request.signal)
    if (!request.signal.aborted) data.value = result
  } catch {
    if (!request.signal.aborted) error.value = true
  } finally {
    if (!request.signal.aborted) loading.value = false
  }
}
watch(() => props.datastream.id, load, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>
<style scoped>
.profile-preview {
  display: flex;
  align-items: center;
  gap: var(--hs-space-12);
}
.profile-preview-button {
  width: 80px;
  height: 64px;
  flex-shrink: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  border-radius: var(--hs-radius-sm);
}
.profile-preview-button:focus-visible {
  outline: 2px solid var(--hs-primary);
}
.profile-preview-button svg {
  width: 100%;
  height: 100%;
}
.profile-preview-area {
  fill: var(--hs-primary);
  opacity: 0.12;
}
.profile-preview-line {
  stroke: var(--hs-primary);
  stroke-width: 2;
  fill: none;
}
.profile-preview-axis {
  stroke: var(--hs-border);
  stroke-width: 1;
  fill: none;
}
</style>
