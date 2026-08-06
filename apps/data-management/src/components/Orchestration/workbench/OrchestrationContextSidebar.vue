<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="flex items-center">
        <span class="sidebar-title">{{ title }}</span>
        <button
          v-if="isIngestion && canCreate"
          type="button"
          class="sidebar-add ml-auto"
          :style="{ background: accent }"
          :aria-label="addLabel"
          @click="$emit('create')"
        >
          <v-icon :icon="mdiPlus" size="16" color="white" />
        </button>
        <v-tooltip v-else-if="isIngestion" location="top">
          <template #activator="{ props: tooltipProps }">
            <span v-bind="tooltipProps" class="ml-auto inline-flex">
              <button
                type="button"
                class="sidebar-add"
                :style="{ background: accent, opacity: 0.5 }"
                disabled
                :aria-label="addLabel"
              >
                <v-icon :icon="mdiPlus" size="16" color="white" />
              </button>
            </span>
          </template>
          <span>{{ READ_ONLY_TOOLTIP }}</span>
        </v-tooltip>
      </div>
      <div class="sidebar-search">
        <v-icon :icon="mdiMagnify" size="16" class="sidebar-search-icon" />
        <input
          :value="search"
          :placeholder="`Search ${title.toLowerCase()}…`"
          class="sidebar-search-input"
          @input="search = ($event.target as HTMLInputElement).value"
        />
      </div>
    </div>

    <div class="sidebar-list">
      <template v-if="isIngestion">
        <div
          v-for="dc in connections"
          :key="dc.id"
          class="sidebar-item sidebar-item--connection"
          :class="{ selected: selectedConnectionId === dc.id }"
          :style="
            selectedConnectionId === dc.id
              ? { background: accent, color: 'white' }
              : {}
          "
          @click="$emit('select-connection', dc.id)"
        >
          <span
            class="sidebar-dot"
            :style="{
              background:
                selectedConnectionId === dc.id
                  ? 'rgba(255,255,255,0.7)'
                  : dotColorForConnection(dc.id),
            }"
          />
          <div class="sidebar-item-body">
            <div class="sidebar-item-title">{{ dc.name }}</div>
            <div class="sidebar-item-meta">
              <span class="sidebar-item-meta-text">
                {{ taskCountForConnection(dc.id) }} task{{
                  taskCountForConnection(dc.id) === 1 ? '' : 's'
                }}
                <span v-if="dc.payload?.type">· {{ dc.payload.type }}</span>
              </span>
              <span class="sidebar-item-actions">
                <button
                  v-if="canEdit"
                  type="button"
                  class="sidebar-item-action"
                  :class="{
                    'sidebar-item-action--selected':
                      selectedConnectionId === dc.id,
                  }"
                  :aria-label="`Edit ${dc.name}`"
                  @click.stop="$emit('edit-connection', dc)"
                >
                  <v-icon :icon="mdiPencil" size="15" />
                </button>
                <v-tooltip v-else location="top">
                  <template #activator="{ props: tooltipProps }">
                    <span v-bind="tooltipProps" class="inline-flex">
                      <button
                        type="button"
                        class="sidebar-item-action"
                        :class="{
                          'sidebar-item-action--selected':
                            selectedConnectionId === dc.id,
                        }"
                        disabled
                        :aria-label="`Edit ${dc.name}`"
                      >
                        <v-icon :icon="mdiPencil" size="15" />
                      </button>
                    </span>
                  </template>
                  <span>{{ READ_ONLY_TOOLTIP }}</span>
                </v-tooltip>
                <button
                  v-if="canDelete"
                  type="button"
                  class="sidebar-item-action sidebar-item-action--danger"
                  :class="{
                    'sidebar-item-action--selected':
                      selectedConnectionId === dc.id,
                  }"
                  :aria-label="`Delete ${dc.name}`"
                  @click.stop="$emit('delete-connection', dc)"
                >
                  <v-icon :icon="mdiTrashCanOutline" size="15" />
                </button>
                <v-tooltip v-else location="top">
                  <template #activator="{ props: tooltipProps }">
                    <span v-bind="tooltipProps" class="inline-flex">
                      <button
                        type="button"
                        class="sidebar-item-action sidebar-item-action--danger"
                        :class="{
                          'sidebar-item-action--selected':
                            selectedConnectionId === dc.id,
                        }"
                        disabled
                        :aria-label="`Delete ${dc.name}`"
                      >
                        <v-icon :icon="mdiTrashCanOutline" size="15" />
                      </button>
                    </span>
                  </template>
                  <span>{{ READ_ONLY_TOOLTIP }}</span>
                </v-tooltip>
              </span>
            </div>
          </div>
          <span
            v-if="
              selectedConnectionId !== dc.id &&
              issueCountForConnection(dc.id) > 0
            "
            class="sidebar-item-badge"
          >
            {{ issueCountForConnection(dc.id) }}
          </span>
        </div>
        <div v-if="connections.length === 0" class="sidebar-empty">
          No data connections yet.
        </div>
      </template>

      <template v-else>
        <div
          v-for="thing in sites"
          :key="thing.id"
          class="sidebar-item"
          :class="{ selected: selectedThingId === thing.id }"
          :style="
            selectedThingId === thing.id
              ? { background: accent, color: 'white' }
              : {}
          "
          @click="$emit('select-site', thing.id)"
        >
          <span
            class="sidebar-dot"
            :style="{
              background:
                selectedThingId === thing.id
                  ? 'rgba(255,255,255,0.7)'
                  : dotColorForSite(thing.id),
            }"
          />
          <div class="sidebar-item-body">
            <div class="sidebar-item-title">{{ thing.name }}</div>
            <div class="sidebar-item-meta">
              {{ taskCountForSite(thing.id) }} task{{
                taskCountForSite(thing.id) === 1 ? '' : 's'
              }}
              <span v-if="isQuality && violationCountForSite(thing.id) > 0">
                · {{ violationCountForSite(thing.id) }} violated rule{{
                  violationCountForSite(thing.id) === 1 ? '' : 's'
                }}
              </span>
            </div>
          </div>
          <span
            v-if="
              selectedThingId !== thing.id && issueCountForSite(thing.id) > 0
            "
            class="sidebar-item-badge"
          >
            {{ issueCountForSite(thing.id) }}
          </span>
        </div>
        <div v-if="sites.length === 0" class="sidebar-empty">No sites yet.</div>
      </template>
    </div>

    <div v-if="isIngestion" class="sidebar-footer">
      <button
        v-if="canCreate"
        type="button"
        class="sidebar-footer-btn"
        :style="{ color: accent, borderColor: accent + '66' }"
        @click="$emit('create')"
      >
        <v-icon :icon="mdiPlus" size="16" class="mr-1" />
        {{ addLabel }}
      </button>
      <v-tooltip v-else location="top">
        <template #activator="{ props: tooltipProps }">
          <span v-bind="tooltipProps" class="inline-flex w-full">
            <button
              type="button"
              class="sidebar-footer-btn"
              :style="{ color: accent, borderColor: accent + '66' }"
              disabled
            >
              <v-icon :icon="mdiPlus" size="16" class="mr-1" />
              {{ addLabel }}
            </button>
          </span>
        </template>
        <span>{{ READ_ONLY_TOOLTIP }}</span>
      </v-tooltip>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { mdiMagnify, mdiPencil, mdiPlus, mdiTrashCanOutline } from '@mdi/js'
import type { DataConnection, ThingTaskSummary } from '@hydroserver/client'
import { useOrchestrationStore } from '@/store/orchestration'
import { READ_ONLY_TOOLTIP, TAB_META } from './orchestrationTabs'

const {
  activeTab,
  selectedConnectionId,
  selectedThingId,
  sidebarSearch: search,
} = storeToRefs(useOrchestrationStore())

const props = withDefaults(
  defineProps<{
    connections: DataConnection[]
    sites: ThingTaskSummary[]
    canCreate: boolean
    canEdit: boolean
    canDelete: boolean
    taskCountForConnection: (id: string) => number
    issueCountForConnection: (id: string) => number
    taskCountForSite: (id: string) => number
    issueCountForSite: (id: string) => number
    violationCountForSite?: (id: string) => number
    dotColorForConnection: (id: string) => string
    dotColorForSite: (id: string) => string
  }>(),
  {
    violationCountForSite: () => () => 0,
  }
)

defineEmits<{
  (e: 'select-connection', id: string): void
  (e: 'select-site', id: string): void
  (e: 'edit-connection', connection: DataConnection): void
  (e: 'delete-connection', connection: DataConnection): void
  (e: 'create'): void
}>()

const isIngestion = computed(() => activeTab.value === 'ingestion')
const isQuality = computed(() => activeTab.value === 'quality')
const accent = computed(() => TAB_META[activeTab.value].accent)
const title = computed(() => (isIngestion.value ? 'Connections' : 'Sites'))
const addLabel = computed(() =>
  isIngestion.value ? 'Add data connection' : 'Add site'
)
</script>

<style scoped>
.sidebar {
  width: 260px;
  border-right: 1px solid var(--hs-border);
  background: var(--hs-surface-muted);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-height: 0;
}
/* The accent bar that used to sit here now spans the nav rail + this
   sidebar together — see .orchestration-nav-column in Orchestration.vue —
   so it's anchored to the page edge instead of floating in from 88px. */
.sidebar-header {
  padding: var(--hs-space-10) var(--hs-space-16) var(--hs-space-8);
  border-bottom: 1px solid var(--hs-border);
}
.sidebar-title {
  font-size: var(--hs-font-2xs);
  font-weight: 700;
  color: var(--hs-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.7px;
}
.sidebar-add {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: var(--hs-radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.sidebar-search {
  position: relative;
  margin-top: var(--hs-space-8);
}
.sidebar-search-icon {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--hs-input-border);
  pointer-events: none;
}
.sidebar-search-input {
  width: 100%;
  border: 1px solid var(--hs-input-border);
  border-radius: var(--hs-radius-pill);
  height: 30px;
  padding-left: 30px;
  padding-right: var(--hs-space-10);
  font-size: var(--hs-font-sm);
  outline: none;
  background: var(--hs-surface);
}
.sidebar-list {
  flex: 1;
  overflow-y: auto;
}
.sidebar-item {
  position: relative;
  padding: var(--hs-space-10) var(--hs-space-16);
  cursor: pointer;
  border-bottom: 1px solid var(--hs-border);
  display: flex;
  align-items: flex-start;
  gap: var(--hs-space-10);
  transition: background 0.1s;
}
.sidebar-item:not(.selected):hover {
  background: rgba(0, 0, 0, 0.035);
}
.sidebar-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}
.sidebar-item-body {
  flex: 1;
  min-width: 0;
}
.sidebar-item--connection .sidebar-item-body {
  padding-right: 62px;
}
.sidebar-item-title {
  font-size: var(--hs-font-sm);
  color: inherit;
}
.sidebar-item.selected .sidebar-item-title {
  font-weight: 600;
}
.sidebar-item-meta {
  font-size: var(--hs-font-2xs);
  color: var(--hs-text-secondary);
  margin-top: var(--hs-space-2);
  min-height: 24px;
  display: flex;
  align-items: center;
  gap: var(--hs-space-6);
}
.sidebar-item.selected .sidebar-item-meta {
  color: rgba(255, 255, 255, 0.7);
}
.sidebar-item-meta-text {
  min-width: 0;
}
.sidebar-item-badge {
  background: var(--hs-danger-bg);
  color: var(--hs-danger);
  border-radius: var(--hs-radius-pill);
  padding: 1px var(--hs-space-6);
  font-size: var(--hs-font-2xs);
  font-weight: 700;
}
.sidebar-item-actions {
  position: absolute;
  right: 14px;
  bottom: 12px;
  display: flex;
  align-items: center;
  gap: var(--hs-space-2);
  opacity: 0;
  transition: opacity 0.1s;
}
.sidebar-item:hover .sidebar-item-actions,
.sidebar-item:focus-within .sidebar-item-actions,
.sidebar-item.selected .sidebar-item-actions {
  opacity: 1;
}
.sidebar-item-action {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--hs-radius-sm);
  color: var(--hs-text-secondary);
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.sidebar-item-action:hover:not(:disabled) {
  /* rgb(73, 69, 79) is --hs-text-secondary; rgba() can't reference a var()
     directly, so the triple is kept in sync with it by hand here. */
  background: rgba(73, 69, 79, 0.12);
}
.sidebar-item-action--danger {
  color: var(--hs-danger);
}
.sidebar-item-action--danger:hover:not(:disabled) {
  background: rgba(179, 38, 30, 0.1);
}
.sidebar-item-action--selected {
  color: white;
}
.sidebar-item-action--selected:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.18);
}
.sidebar-item-action:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.sidebar-empty {
  padding: var(--hs-space-16) var(--hs-space-16);
  font-size: var(--hs-font-sm);
  color: var(--hs-text-muted);
}
.sidebar-footer {
  padding: var(--hs-space-10) var(--hs-space-16);
  border-top: 1px solid var(--hs-border);
}
.sidebar-footer-btn {
  background: none;
  border: 1px dashed;
  border-radius: var(--hs-radius-md);
  padding: var(--hs-space-6) 0;
  width: 100%;
  font-size: var(--hs-font-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.sidebar-footer-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
