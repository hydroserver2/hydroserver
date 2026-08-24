<template>
  <div class="hs-selection-sidebar">
    <header class="hs-selection-sidebar__header">
      <div class="hs-selection-sidebar__heading">
        <span class="hs-selection-sidebar__title hs-label">{{ title }}</span>
        <div v-if="$slots.actions" class="hs-selection-sidebar__actions">
          <slot name="actions" />
        </div>
      </div>

      <HsSearchInput
        v-if="!hideSearch"
        :model-value="modelValue"
        class="hs-selection-sidebar__search"
        shape="pill"
        :placeholder="searchPlaceholder || `Search ${title.toLowerCase()}…`"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </header>

    <div class="hs-selection-list">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import HsSearchInput from '@/components/base/HsSearchInput.vue'

withDefaults(
  defineProps<{
    title: string
    modelValue?: string
    searchPlaceholder?: string
    hideSearch?: boolean
  }>(),
  {
    modelValue: '',
    searchPlaceholder: '',
    hideSearch: false,
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<style scoped>
.hs-selection-sidebar {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.hs-selection-sidebar__header {
  box-sizing: border-box;
  min-height: 93px;
  padding: var(--hs-space-12) var(--hs-space-16) var(--hs-space-8);
  border-bottom: 1px solid var(--hs-border);
}

.hs-selection-sidebar__heading {
  display: flex;
  align-items: center;
}

.hs-selection-sidebar__title {
  color: var(--hs-text-secondary);
  letter-spacing: 0.7px;
  text-transform: uppercase;
}

.hs-selection-sidebar__actions {
  display: inline-flex;
  align-items: center;
  margin-left: auto;
}

.hs-selection-sidebar__search {
  --hs-search-text: var(--hs-text-secondary);
  max-width: none;
  margin-top: var(--hs-space-8);
}
</style>
