<template>
  <nav class="nav-rail">
    <div class="rail-main">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="rail-btn"
        :class="{ active: activeView === 'tasks' && activeTab === tab.id }"
        :style="
          activeView === 'tasks' && activeTab === tab.id
            ? { '--accent': tab.accent, '--accent-light': tab.accentLight }
            : {}
        "
        @click="$emit('select-tab', tab.id)"
      >
        <span
          class="rail-pill"
          :style="
            activeView === 'tasks' && activeTab === tab.id
              ? { background: tab.accentLight }
              : {}
          "
        >
          <v-icon
            :icon="tab.icon"
            size="22"
            :color="
              activeView === 'tasks' && activeTab === tab.id
                ? tab.accent
                : undefined
            "
          />
          <span v-if="tab.issues > 0" class="rail-badge">{{ tab.issues }}</span>
        </span>
        <span
          class="rail-label"
          :style="
            activeView === 'tasks' && activeTab === tab.id
              ? { color: tab.accent, fontWeight: 600 }
              : {}
          "
        >
          {{ tab.short }}
        </span>
      </button>
    </div>

    <div class="rail-bottom">
      <button
        type="button"
        class="rail-btn"
        @click="$emit('open-workspaces')"
      >
        <span
          class="rail-pill"
          :style="
            activeView === 'workspaces'
              ? { background: WORKSPACE_ACCENT_LIGHT }
              : {}
          "
        >
          <v-icon
            :icon="mdiBriefcaseOutline"
            size="22"
            :color="activeView === 'workspaces' ? WORKSPACE_ACCENT : undefined"
          />
        </span>
        <span
          class="rail-label"
          :style="
            activeView === 'workspaces'
              ? { color: WORKSPACE_ACCENT, fontWeight: 600 }
              : {}
          "
        >
          Workspaces
        </span>
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
import {
  WORKSPACE_ACCENT,
  WORKSPACE_ACCENT_LIGHT,
  type ActiveView,
  type TabDefinition,
  type TabId,
} from './orchestrationTabs'

defineProps<{
  tabs: TabDefinition[]
  activeTab: TabId
  activeView: ActiveView
}>()

defineEmits<{
  (e: 'select-tab', id: TabId): void
  (e: 'open-workspaces'): void
  (e: 'open-hydro-loader'): void
}>()
</script>

<style scoped>
.nav-rail {
  width: 88px;
  border-right: 1px solid #e8e8e8;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  flex-shrink: 0;
}
.rail-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  width: 100%;
}
.rail-bottom {
  margin-top: auto;
  width: 100%;
  padding-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
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
.rail-badge {
  position: absolute;
  top: 1px;
  right: 4px;
  background: #b71c1c;
  color: white;
  border-radius: 8px;
  min-width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  padding: 0 3px;
  line-height: 1;
}
.rail-label {
  font-size: 10.5px;
  color: #49454f;
  line-height: 1.2;
  text-align: center;
}
</style>
