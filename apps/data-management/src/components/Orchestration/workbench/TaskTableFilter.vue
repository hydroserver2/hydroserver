<template>
  <HsTableFilterMenu
    :title="title"
    :label="label"
    :section-label="label === 'Status' ? 'Statuses' : 'Task types'"
    :options="options.map((option) => ({ ...option, label: option.title }))"
    :selected="selected"
    :show-checkboxes="showCheckboxes"
    :searchable="false"
    @toggle="emit('toggle', $event)"
  >
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
  </HsTableFilterMenu>
</template>

<script setup lang="ts">
import { HsTableFilterMenu } from '@hydroserver/design-system/vue'
import { mdiChevronDown } from '@mdi/js'

withDefaults(
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
    showCheckboxes?: boolean
  }>(),
  { showCheckboxes: false }
)

const emit = defineEmits<{
  toggle: [value: string]
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

.task-filter-button--active {
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
</style>
