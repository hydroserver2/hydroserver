<template>
  <div class="health-pills">
    <span class="count hs-text-2xs">
      {{ tasks.length }} task{{ tasks.length === 1 ? '' : 's' }}
    </span>
    <component
      :is="interactive ? 'button' : 'span'"
      v-for="entry in pills"
      :key="entry.status"
      class="pill hs-text-2xs font-weight-medium"
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
import { taskStatusColor } from '@/utils/orchestration/taskStatusColors'

interface Props {
  tasks: Array<{ statusName?: string | null }>
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

const pills = computed(() => {
  const counts = new Map<string, number>()
  for (const task of props.tasks) {
    const key = task.statusName || 'Unknown'
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return Array.from(counts.entries()).map(([status, count]) => ({
    status,
    count,
    color: taskStatusColor(status),
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
  color: #49454f;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.pill--interactive {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 2px 8px;
  cursor: pointer;
  font-family: inherit;
  transition:
    background 0.12s ease,
    border-color 0.12s ease;
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
