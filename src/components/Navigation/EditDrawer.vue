<template>
  <div class="edit-drawer d-flex flex-column fill-height">
    <div class="flex-grow-1 overflow-y-auto" style="min-height: 0">
      <!-- Collapsible Filter Data section. Same chevron + primary-
           tinted icon + caption treatment as the select drawer so
           both drawers read as the same family of controls. -->
      <div
        class="edit-drawer__section-header d-flex align-center gap-1 px-3 py-1"
        role="button"
        tabindex="0"
        @click="filterCollapsed = !filterCollapsed"
        @keydown.enter.prevent="filterCollapsed = !filterCollapsed"
        @keydown.space.prevent="filterCollapsed = !filterCollapsed"
      >
        <v-icon
          size="16"
          :icon="filterCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-down'"
        />
        <v-icon icon="mdi-filter-variant" color="primary" size="16" />
        <span class="text-caption font-weight-medium">Filter Data</span>
      </div>
      <v-list v-show="!filterCollapsed" class="py-2" density="compact" nav>
        <v-list-item
          v-for="item in filterPoints"
          :key="item.id"
          rounded="lg"
          class="mb-1"
          :active="selectedOperation === item.id"
          :data-testid="`op-${item.id}`"
          @click="selectOperation(item.id)"
        >
          <template v-slot:prepend>
            <v-avatar size="32" :color="colorForOperation(item)" variant="flat">
              <v-icon size="18" color="white" :icon="item.icon" />
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ item.title }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ item.description }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <v-divider />

      <!-- Collapsible Edit Data section. -->
      <div
        class="edit-drawer__section-header d-flex align-center gap-1 px-3 py-1"
        role="button"
        tabindex="0"
        @click="editCollapsed = !editCollapsed"
        @keydown.enter.prevent="editCollapsed = !editCollapsed"
        @keydown.space.prevent="editCollapsed = !editCollapsed"
      >
        <v-icon
          size="16"
          :icon="editCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-down'"
        />
        <v-icon icon="mdi-pencil" color="primary" size="16" />
        <span class="text-caption font-weight-medium">Edit Data</span>
      </div>
      <v-list v-show="!editCollapsed" class="py-2" density="compact" nav>
        <v-list-item
          v-for="item in editData"
          :key="item.id"
          rounded="lg"
          class="mb-1"
          :active="selectedOperation === item.id"
          :disabled="item.requiresSelection && !selectedData?.length"
          :data-testid="`op-${item.id}`"
          @click="selectOperation(item.id)"
        >
          <template v-slot:prepend>
            <v-avatar size="32" :color="colorForOperation(item)" variant="flat">
              <v-icon size="18" color="white" :icon="item.icon" />
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ item.title }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ item.description }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <v-divider />

      <!-- Collapsible Add Data section. -->
      <div
        class="edit-drawer__section-header d-flex align-center gap-1 px-3 py-1"
        role="button"
        tabindex="0"
        @click="addCollapsed = !addCollapsed"
        @keydown.enter.prevent="addCollapsed = !addCollapsed"
        @keydown.space.prevent="addCollapsed = !addCollapsed"
      >
        <v-icon
          size="16"
          :icon="addCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-down'"
        />
        <v-icon icon="mdi-plus-circle-outline" color="primary" size="16" />
        <span class="text-caption font-weight-medium">Add Data</span>
      </div>
      <v-list v-show="!addCollapsed" class="py-2" density="compact" nav>
        <v-list-item
          v-for="item in addData"
          :key="item.id"
          rounded="lg"
          class="mb-1"
          :active="selectedOperation === item.id"
          :data-testid="`op-${item.id}`"
          @click="selectOperation(item.id)"
        >
          <template v-slot:prepend>
            <v-avatar size="32" :color="colorForOperation(item)" variant="flat">
              <v-icon size="18" color="white" :icon="item.icon" />
            </v-avatar>
          </template>
          <v-list-item-title class="text-body-2 font-weight-medium">
            {{ item.title }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ item.description }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { useUIStore } from '@/store/userInterface'
import {
  operationsByGroup,
  colorForOperation,
} from '@/components/EditData/operations'
import { usePersistedFlag } from '@/composables/useResizable'

const { selectedData } = storeToRefs(useDataVisStore())
const { selectedOperation } = storeToRefs(useUIStore())

const filterPoints = operationsByGroup.filter
const editData = operationsByGroup.edit
const addData = operationsByGroup.add

// Persisted collapse flags — keyed under `qc:editorLayout:*` so
// per-section collapse state survives reloads alongside the
// sibling drawer/panel widths.
const filterCollapsed = usePersistedFlag(
  'qc:editorLayout:opsFilterCollapsed',
  false
)
const editCollapsed = usePersistedFlag(
  'qc:editorLayout:opsEditCollapsed',
  false
)
const addCollapsed = usePersistedFlag('qc:editorLayout:opsAddCollapsed', false)

function selectOperation(id: string) {
  // Toggle off if the same operation is clicked again, otherwise switch.
  selectedOperation.value = selectedOperation.value === id ? null : id
}
</script>

<style scoped>
/* Section header — matches `.select-drawer__section-header` so the
   filter drawer and the edit drawer's operation list read as a
   single family of controls. */
.edit-drawer__section-header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  cursor: pointer;
  min-height: 28px;
}
.edit-drawer__section-header:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
}
.edit-drawer__section-header:focus {
  outline: none;
  background-color: rgba(var(--v-theme-primary), 0.08);
}

/* The remaining rules all `:deep()` into Vuetify's v-list-item
   internals to allow text wrapping and reclaim padding inside a
   narrow (~220 px) drawer. No utility-class equivalents. */

/* Allow multi-line titles and descriptions instead of Vuetify's default
   single-line-with-ellipsis. Vuetify sets `overflow: hidden; text-overflow:
   ellipsis; white-space: nowrap` on these with high specificity (including
   variants like `.v-list-item--two-line .v-list-item-title`), and also
   applies `-webkit-line-clamp` via the `lines="two"` prop. We override
   with !important so the row can grow vertically for long descriptions. */
:deep(.v-list-item-title),
:deep(.v-list-item-subtitle) {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  -webkit-line-clamp: unset !important;
  line-clamp: unset !important;
  display: block !important;
  line-height: 1.3 !important;
  word-break: normal;
  overflow-wrap: anywhere;
}

/* Let the text column use the full available width inside the list
   item. Vuetify's default padding on `.v-list-item__content` and
   `.v-list-item` itself leaves ~10–12 px wasted on each side, which
   measurably narrows multi-line descriptions in a 220 px drawer. */
:deep(.v-list-item) {
  padding-inline: 10px !important;
}

:deep(.v-list-item__content) {
  overflow: visible !important;
  min-width: 0;
  flex: 1 1 100%;
}

:deep(.v-list-item__spacer) {
  width: 10px !important;
}

:deep(.v-list-item-subtitle) {
  opacity: 0.75;
}

/* Align the icon avatar to the top so it doesn't drift down next to
   two-line text blocks. */
:deep(.v-list-item__prepend) {
  align-self: flex-start;
  padding-top: 4px;
}

:deep(.v-list-item--disabled) {
  opacity: 0.55;
}
</style>
