<template>
  <div class="edit-drawer d-flex flex-column fill-height">
    <div class="flex-grow-1 overflow-y-auto" style="min-height: 0">
      <div
        class="edit-drawer__section-header d-flex align-center ga-1 px-3 py-1 cursor-pointer"
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
        <span class="text-body-small font-weight-medium">Filter Data</span>
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
          <v-list-item-title class="text-body-medium font-weight-medium">
            {{ item.title }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-body-small">
            {{ item.description }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <v-divider />

      <div
        class="edit-drawer__section-header d-flex align-center ga-1 px-3 py-1 cursor-pointer"
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
        <span class="text-body-small font-weight-medium">Edit Data</span>
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
          <v-list-item-title class="text-body-medium font-weight-medium">
            {{ item.title }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-body-small">
            {{ item.description }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <v-divider />

      <div
        class="edit-drawer__section-header d-flex align-center ga-1 px-3 py-1 cursor-pointer"
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
        <span class="text-body-small font-weight-medium">Add Data</span>
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
          <v-list-item-title class="text-body-medium font-weight-medium">
            {{ item.title }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-body-small">
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
  selectedOperation.value = selectedOperation.value === id ? null : id
}
</script>

<style scoped>
.edit-drawer__section-header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 28px;
}
.edit-drawer__section-header:hover,
.edit-drawer__section-header:focus {
  background-color: rgba(var(--v-theme-primary), 0.08);
}
.edit-drawer__section-header:focus {
  outline: none;
}

/* Override Vuetify's nowrap+ellipsis on list-item title/subtitle so
   descriptions can wrap in the narrow (~220px) drawer. */
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

:deep(.v-list-item__prepend) {
  align-self: flex-start;
  padding-top: 4px;
}

:deep(.v-list-item--disabled) {
  opacity: 0.55;
}
</style>
