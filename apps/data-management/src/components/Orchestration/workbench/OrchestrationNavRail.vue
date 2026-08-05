<template>
  <nav class="nav-rail">
    <div class="rail-main">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="rail-btn"
        :class="{ active: activeTab === tab.id }"
        :style="
          activeTab === tab.id
            ? { '--accent': tab.accent, '--accent-light': tab.accentLight }
            : {}
        "
        @click="$emit('select-tab', tab.id)"
      >
        <span
          class="rail-pill"
          :style="activeTab === tab.id ? { background: tab.accentLight } : {}"
        >
          <v-icon
            :icon="tab.icon"
            size="22"
            :color="activeTab === tab.id ? tab.accent : undefined"
          />
          <span v-if="tab.issues > 0" class="rail-badge">{{ tab.issues }}</span>
        </span>
        <span
          class="rail-label"
          :style="
            activeTab === tab.id ? { color: tab.accent, fontWeight: 600 } : {}
          "
        >
          {{ tab.short }}
        </span>
      </button>
    </div>

    <div class="rail-bottom">
      <button type="button" class="rail-btn" @click="$emit('open-workspaces')">
        <span class="rail-pill">
          <v-icon :icon="mdiBriefcaseOutline" size="22" />
        </span>
        <span class="rail-label">Workspaces</span>
      </button>

      <button
        type="button"
        class="rail-btn rail-btn-secondary rail-link"
        @click="$emit('open-hydro-loader')"
      >
        <span class="rail-pill rail-pill-secondary">
          <v-icon :icon="mdiDownloadBoxOutline" size="22" />
        </span>
        <span class="rail-label">Download data loader</span>
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { mdiBriefcaseOutline, mdiDownloadBoxOutline } from '@mdi/js'
import { storeToRefs } from 'pinia'
import { useOrchestrationStore } from '@/store/orchestration'
import { type TabDefinition, type TabId } from './orchestrationTabs'

defineProps<{
  tabs: TabDefinition[]
}>()

defineEmits<{
  (e: 'select-tab', id: TabId): void
  (e: 'open-workspaces'): void
  (e: 'open-hydro-loader'): void
}>()

const { activeTab } = storeToRefs(useOrchestrationStore())
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
.rail-bottom {
  margin-top: auto;
  width: 100%;
  padding-top: var(--hs-space-12);
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-2);
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
.rail-link {
  text-decoration: none;
  color: inherit;
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
.rail-btn-secondary {
  color: var(--hs-text-secondary);
}
.rail-btn-secondary:hover .rail-pill-secondary {
  background: rgba(21, 101, 192, 0.08);
}
.rail-pill-secondary {
  background: transparent;
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
  font-size: var(--hs-font-2xs);
  font-weight: 700;
  padding: 0 3px;
  line-height: 1;
}
.rail-label {
  font-size: var(--hs-font-2xs);
  color: var(--hs-text-secondary);
  line-height: 1.2;
  text-align: center;
}
</style>
