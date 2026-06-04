<template>
  <div class="health-pills">
    <span class="count">
      {{ tasks.length }} task{{ tasks.length === 1 ? '' : 's' }}
    </span>
    <component
      :is="interactive ? 'button' : 'span'"
      v-for="entry in pills"
      :key="entry.status"
      class="pill"
      :class="{
        'pill--interactive': interactive,
        'pill--active': interactive && activeStatuses.includes(entry.status),
      }"
      :type="interactive ? 'button' : undefined"
      :aria-pressed="
        interactive ? activeStatuses.includes(entry.status) : undefined
      "
      :style="{ color: entry.color }"
      @click="interactive && $emit('toggle-status', entry.status)"
    >
      <span class="dot" :style="{ background: entry.color }" />
      {{ entry.count }} {{ entry.status.toLowerCase() }}
    </component>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  tasks: Array<{ statusSort?: string | null }>
  interactive?: boolean
  activeStatuses?: string[]
}
const props = withDefaults(defineProps<Props>(), {
  interactive: false,
  activeStatuses: () => [],
})

defineEmits<{
  (e: 'toggle-status', status: string): void
}>()

const STATUS_COLORS: Record<string, string> = {
  OK: '#2E7D32',
  'Behind schedule': '#BF360C',
  'Needs attention': '#B71C1C',
  'Loading paused': '#546E7A',
  Pending: '#1565C0',
  Unknown: '#9E9E9E',
}

const pills = computed(() => {
  const counts = new Map<string, number>()
  for (const task of props.tasks) {
    const key = task.statusSort || 'Unknown'
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return Array.from(counts.entries()).map(([status, count]) => ({
    status,
    count,
    color: STATUS_COLORS[status] ?? '#9E9E9E',
  }))
})
</script>

<style scoped>
.health-pills {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.count {
  font-size: 11px;
  color: #49454f;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
}
.pill--interactive {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 2px 8px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.12s ease, border-color 0.12s ease;
}
.pill--interactive:hover {
  background: color-mix(in srgb, currentColor 10%, transparent);
}
.pill--active {
  border-color: currentColor;
  background: color-mix(in srgb, currentColor 14%, transparent);
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
</style>
