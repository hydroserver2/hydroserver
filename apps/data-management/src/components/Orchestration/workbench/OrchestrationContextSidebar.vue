<template>
  <HsSelectionSidebar v-model="search" :title="title">
    <template v-if="isIngestion" #actions>
      <button
        v-if="canCreate"
        type="button"
        class="hs-sidebar-action"
        aria-label="Add data connection"
        @click="$emit('create')"
      >
        <v-icon :icon="mdiPlus" size="16" />
      </button>
      <v-tooltip v-else location="top">
        <template #activator="{ props: tooltipProps }">
          <span v-bind="tooltipProps" class="inline-flex">
            <button
              type="button"
              class="hs-sidebar-action"
              disabled
              aria-label="Add data connection"
            >
              <v-icon :icon="mdiPlus" size="16" />
            </button>
          </span>
        </template>
        <span>{{ READ_ONLY_TOOLTIP }}</span>
      </v-tooltip>
    </template>

    <template v-if="isIngestion">
      <HsSelectionListItem
        v-for="connection in connections"
        :key="connection.id"
        :title="connection.name"
        :selected="selectedConnectionId === connection.id"
        :status-color="dotColorForConnection(connection.id)"
        :badge="
          selectedConnectionId !== connection.id &&
          issueCountForConnection(connection.id) > 0
            ? issueCountForConnection(connection.id)
            : null
        "
        @select="$emit('select-connection', connection.id)"
      >
        <template #metadata>
          {{ taskCountForConnection(connection.id) }} task{{
            taskCountForConnection(connection.id) === 1 ? '' : 's'
          }}
          <span v-if="connection.payload?.type">
            · {{ connection.payload.type }}
          </span>
        </template>
        <template #actions>
          <button
            v-if="canEdit"
            type="button"
            class="hs-selection-list__action"
            :aria-label="`Edit ${connection.name}`"
            @click.stop="$emit('edit-connection', connection)"
          >
            <v-icon :icon="mdiPencil" size="15" />
          </button>
          <v-tooltip v-else location="top">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <button
                  type="button"
                  class="hs-selection-list__action"
                  disabled
                  :aria-label="`Edit ${connection.name}`"
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
            class="hs-selection-list__action hs-selection-list__action--danger"
            :aria-label="`Delete ${connection.name}`"
            @click.stop="$emit('delete-connection', connection)"
          >
            <v-icon :icon="mdiTrashCanOutline" size="15" />
          </button>
          <v-tooltip v-else location="top">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <button
                  type="button"
                  class="hs-selection-list__action hs-selection-list__action--danger"
                  disabled
                  :aria-label="`Delete ${connection.name}`"
                >
                  <v-icon :icon="mdiTrashCanOutline" size="15" />
                </button>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
        </template>
      </HsSelectionListItem>

      <div
        v-if="connections.length === 0"
        class="hs-selection-list__empty hs-text-sm"
      >
        No data connections yet.
      </div>
    </template>

    <template v-else>
      <HsSelectionListItem
        v-for="monitoringSite in sites"
        :key="monitoringSite.id"
        :title="monitoringSite.name"
        :selected="selectedMonitoringSiteId === monitoringSite.id"
        :status-color="dotColorForSite(monitoringSite.id)"
        :badge="
          selectedMonitoringSiteId !== monitoringSite.id &&
          issueCountForSite(monitoringSite.id) > 0
            ? issueCountForSite(monitoringSite.id)
            : null
        "
        @select="$emit('select-site', monitoringSite.id)"
      >
        <template #metadata>
          {{ taskCountForSite(monitoringSite.id) }} task{{
            taskCountForSite(monitoringSite.id) === 1 ? '' : 's'
          }}
          <span
            v-if="isQuality && violationCountForSite(monitoringSite.id) > 0"
          >
            · {{ violationCountForSite(monitoringSite.id) }} violated rule{{
              violationCountForSite(monitoringSite.id) === 1 ? '' : 's'
            }}
          </span>
        </template>
      </HsSelectionListItem>

      <div
        v-if="sites.length === 0"
        class="hs-selection-list__empty hs-text-sm"
      >
        No sites yet.
      </div>
    </template>
  </HsSelectionSidebar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { mdiPencil, mdiPlus, mdiTrashCanOutline } from '@mdi/js'
import type {
  DataConnection,
  MonitoringSiteTaskSummary,
} from '@hydroserver/client'
import {
  HsSelectionListItem,
  HsSelectionSidebar,
} from '@hydroserver/design-system/vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { READ_ONLY_TOOLTIP } from './orchestrationTabs'

const {
  activeTab,
  selectedConnectionId,
  selectedMonitoringSiteId,
  sidebarSearch: search,
} = storeToRefs(useOrchestrationStore())

const props = withDefaults(
  defineProps<{
    connections: DataConnection[]
    sites: MonitoringSiteTaskSummary[]
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
const title = computed(() => (isIngestion.value ? 'Connections' : 'Sites'))
</script>
