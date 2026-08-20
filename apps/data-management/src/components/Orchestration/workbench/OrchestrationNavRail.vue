<template>
  <nav class="nav-rail">
    <div class="rail-main">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="rail-btn"
        :class="{ active: activeTab === tab.id }"
        @click="$emit('select-tab', tab.id)"
      >
        <span
          class="rail-pill"
          :style="
            activeTab === tab.id
              ? {
                  background:
                    tab.id === 'ingestion'
                      ? 'rgba(var(--v-theme-primary), 0.12)'
                      : tab.accentLight,
                }
              : {}
          "
        >
          <v-icon
            :icon="tab.icon"
            size="22"
            :style="activeTab === tab.id ? { color: activeColor(tab) } : {}"
          />
          <span
            v-if="tab.issues > 0"
            class="rail-badge hs-label"
            >{{ tab.issues }}</span
          >
        </span>
        <span
          class="rail-label hs-text-2xs"
          :class="{ 'font-weight-semibold': activeTab === tab.id }"
          :style="activeTab === tab.id ? { color: activeColor(tab) } : {}"
        >
          {{ tab.short }}
        </span>
      </button>
    </div>

  </nav>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useOrchestrationStore } from '@/store/orchestration'
import { type TabDefinition, type TabId } from './orchestrationTabs'

defineProps<{
  tabs: TabDefinition[]
}>()

defineEmits<{
  (e: 'select-tab', id: TabId): void
}>()

const { activeTab } = storeToRefs(useOrchestrationStore())

const activeColor = (tab: TabDefinition) =>
  tab.id === 'ingestion' ? 'rgb(var(--v-theme-primary))' : tab.accent
</script>

<style scoped>
.nav-rail {
  width: 88px;
  border-right: 1px solid var(--hs-border);
  background: var(--hs-surface-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--hs-space-16) 0;
  flex-shrink: 0;
}
.rail-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--hs-space-2);
  width: 100%;
}
.rail-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--hs-space-4);
  padding: var(--hs-space-8) var(--hs-space-4);
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
  border-radius: var(--hs-radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background 0.15s;
}
.rail-badge {
  position: absolute;
  top: 1px;
  right: 4px;
  background: var(--hs-danger);
  color: white;
  border-radius: var(--hs-radius-pill);
  min-width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 3px;
  line-height: 1;
}
.rail-label {
  color: var(--hs-text-secondary);
  line-height: 1.2;
  text-align: center;
}
</style>
