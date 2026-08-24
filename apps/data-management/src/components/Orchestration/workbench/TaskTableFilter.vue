<template>
  <v-menu :close-on-content-click="false" location="bottom start" attach="body">
    <template #activator="{ props: menuProps }">
      <v-btn
        v-bind="menuProps"
        variant="text"
        size="small"
        class="task-filter-button"
        :class="{ 'task-filter-button--active': selected.length }"
        :append-icon="mdiChevronDown"
        :aria-label="`${title}${selected.length ? ` (${selected.length} selected)` : ''}`"
        @click.stop
      >
        {{ label }}
        <span v-if="selected.length" class="task-filter-count">
          {{ selected.length }}
        </span>
      </v-btn>
    </template>

    <v-list class="task-filter-menu" density="compact">
      <div class="task-filter-title">{{ title }}</div>
      <v-list-item
        v-for="option in options"
        :key="option.value"
        :class="{
          'task-filter-option--selected': selected.includes(option.value),
        }"
        @click="emit('toggle', option.value)"
      >
        <template #prepend>
          <v-checkbox
            :model-value="selected.includes(option.value)"
            hide-details
            density="compact"
            :aria-label="`${label}: ${option.title}`"
            @click.stop="emit('toggle', option.value)"
          />
        </template>
        <v-list-item-title class="task-filter-option">
          <v-icon
            v-if="option.icon"
            :icon="option.icon"
            size="18"
            :style="{ color: option.color }"
          />
          <span>{{ option.title }}</span>
        </v-list-item-title>
      </v-list-item>
      <v-list-item
        v-if="selected.length"
        class="task-filter-clear"
        @click="emit('clear')"
      >
        <v-list-item-title>Clear filter</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { mdiChevronDown } from '@mdi/js'

defineProps<{
  label: string
  title: string
  options: readonly {
    title: string
    value: string
    icon?: string
    color?: string
  }[]
  selected: readonly string[]
}>()

const emit = defineEmits<{
  toggle: [value: string]
  clear: []
}>()
</script>

<style scoped>
.task-filter-button {
  min-width: auto;
  height: 32px;
  padding: 0 var(--hs-space-8);
  color: var(--hs-text-primary);
  text-transform: none;
}

.task-filter-button--active,
.task-filter-clear {
  color: rgb(var(--v-theme-primary));
}

.task-filter-count {
  min-width: 18px;
  padding: 0 5px;
  margin-left: var(--hs-space-2);
  color: rgb(var(--v-theme-on-primary));
  font-size: var(--hs-font-2xs);
  line-height: 18px;
  text-align: center;
  background: rgb(var(--v-theme-primary));
  border-radius: var(--hs-radius-pill);
}

.task-filter-menu {
  min-width: 260px;
  max-height: 320px;
  padding: var(--hs-space-8) 0;
  overflow-y: auto;
}

.task-filter-title {
  padding: var(--hs-space-8) var(--hs-space-16);
  color: var(--hs-text-primary);
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-semibold);
}

.task-filter-option {
  display: inline-flex;
  gap: var(--hs-space-8);
  align-items: center;
}

.task-filter-option--selected {
  background: var(--hs-surface-muted);
}
</style>
