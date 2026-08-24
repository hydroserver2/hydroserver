<template>
  <HsNavRail
    :items="items"
    :model-value="activeTab"
    aria-label="Job orchestration sections"
    data-testid="nav-rail"
    @update:model-value="selectTab"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import HsNavRail from '@/components/base/HsNavRail.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { type TabDefinition, type TabId } from './orchestrationTabs'

const props = defineProps<{
  tabs: TabDefinition[]
}>()

const emit = defineEmits<{
  (e: 'select-tab', id: TabId): void
}>()

const { activeTab } = storeToRefs(useOrchestrationStore())

const items = computed(() =>
  props.tabs.map((tab) => ({
    id: tab.id,
    label: tab.short,
    icon: tab.icon,
    badge: tab.issues,
    activeColor:
      tab.id === 'ingestion' ? 'rgb(var(--v-theme-primary))' : tab.accent,
    activeBackground:
      tab.id === 'ingestion'
        ? 'rgba(var(--v-theme-primary), 0.12)'
        : tab.accentLight,
  }))
)

const selectTab = (id: string) => emit('select-tab', id as TabId)
</script>
