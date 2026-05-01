<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="flex items-center">
        <span class="sidebar-title">{{ title }}</span>
        <v-tooltip
          v-if="isIngestion"
          location="top"
          :disabled="canEdit"
        >
          <template #activator="{ props: tooltipProps }">
            <span v-bind="tooltipProps" class="ml-auto inline-flex">
              <button
                type="button"
                class="sidebar-add"
                :style="{
                  background: accent,
                  opacity: canEdit ? 1 : 0.5,
                }"
                :disabled="!canEdit"
                :aria-label="addLabel"
                @click="$emit('create')"
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
          @input="$emit('update:search', ($event.target as HTMLInputElement).value)"
        />
      </div>
    </div>

    <div class="sidebar-list">
      <template v-if="isIngestion">
        <div
          v-for="dc in connections"
          :key="dc.id"
          class="sidebar-item"
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
              {{ taskCountForConnection(dc.id) }} task{{
                taskCountForConnection(dc.id) === 1 ? '' : 's'
              }}
              <span v-if="dc.payload?.type">· {{ dc.payload.type }}</span>
            </div>
          </div>
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
              selectedThingId !== thing.id && sidebarBadgeCount(thing.id) > 0
            "
            class="sidebar-item-badge"
          >
            {{ sidebarBadgeCount(thing.id) }}
          </span>
        </div>
        <div v-if="sites.length === 0" class="sidebar-empty">
          No sites yet.
        </div>
      </template>
    </div>

    <div v-if="isIngestion" class="sidebar-footer">
      <v-tooltip location="top" :disabled="canEdit">
        <template #activator="{ props: tooltipProps }">
          <span v-bind="tooltipProps" class="inline-flex w-full">
            <button
              type="button"
              class="sidebar-footer-btn"
              :style="{ color: accent, borderColor: accent + '66' }"
              :disabled="!canEdit"
              @click="$emit('create')"
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
import { mdiMagnify, mdiPlus } from '@mdi/js'
import type { DataConnection, Thing } from '@hydroserver/client'
import { READ_ONLY_TOOLTIP, type TabId } from './orchestrationTabs'

const props = withDefaults(defineProps<{
  activeTab: TabId
  connections: DataConnection[]
  sites: Thing[]
  selectedConnectionId: string | null
  selectedThingId: string | null
  search: string
  title: string
  addLabel: string
  accent: string
  canEdit: boolean
  taskCountForConnection: (id: string) => number
  taskCountForSite: (id: string) => number
  issueCountForSite: (id: string) => number
  violationCountForSite?: (id: string) => number
  dotColorForConnection: (id: string) => string
  dotColorForSite: (id: string) => string
}>(), {
  violationCountForSite: () => () => 0,
})

defineEmits<{
  (e: 'update:search', value: string): void
  (e: 'select-connection', id: string): void
  (e: 'select-site', id: string): void
  (e: 'create'): void
}>()

const isIngestion = computed(() => props.activeTab === 'ingestion')
const isQuality = computed(() => props.activeTab === 'quality')

const sidebarBadgeCount = (thingId: string) =>
  isQuality.value
    ? props.violationCountForSite(thingId)
    : props.issueCountForSite(thingId)
</script>

<style scoped>
.sidebar {
  width: 260px;
  border-right: 1px solid #e8e8e8;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-height: 0;
}
.sidebar-header {
  padding: 11px 14px 10px;
  border-bottom: 1px solid #ebebeb;
}
.sidebar-title {
  font-size: 11px;
  font-weight: 700;
  color: #49454f;
  text-transform: uppercase;
  letter-spacing: 0.7px;
}
.sidebar-add {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.sidebar-search {
  position: relative;
  margin-top: 8px;
}
.sidebar-search-icon {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  color: #cac4d0;
  pointer-events: none;
}
.sidebar-search-input {
  width: 100%;
  border: 1px solid #cac4d0;
  border-radius: 20px;
  height: 30px;
  padding-left: 30px;
  padding-right: 10px;
  font-size: 12px;
  outline: none;
  background: white;
}
.sidebar-list {
  flex: 1;
  overflow-y: auto;
}
.sidebar-item {
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 1px solid #ebebeb;
  display: flex;
  align-items: flex-start;
  gap: 10px;
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
.sidebar-item-title {
  font-size: 13px;
  color: inherit;
}
.sidebar-item.selected .sidebar-item-title {
  font-weight: 600;
}
.sidebar-item-meta {
  font-size: 11px;
  color: #49454f;
  margin-top: 2px;
}
.sidebar-item.selected .sidebar-item-meta {
  color: rgba(255, 255, 255, 0.7);
}
.sidebar-item-badge {
  background: #ffebee;
  color: #b3261e;
  border-radius: 10px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
}
.sidebar-empty {
  padding: 16px 14px;
  font-size: 12px;
  color: #9ca3af;
}
.sidebar-footer {
  padding: 10px 14px;
  border-top: 1px solid #ebebeb;
}
.sidebar-footer-btn {
  background: none;
  border: 1px dashed;
  border-radius: 8px;
  padding: 6px 0;
  width: 100%;
  font-size: 12px;
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
