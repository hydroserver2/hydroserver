<template>
  <v-navigation-drawer
    permanent
    :width="drawerCollapsed ? 36 : drawerWidth"
    elevation="1"
    class="select-drawer"
    :class="{ 'select-drawer--collapsed': drawerCollapsed }"
  >
    <!-- Collapsed rail: single expand chevron, matches the edit
         view's aux-column rail. -->
    <template v-if="drawerCollapsed">
      <div
        class="select-drawer__bar d-flex justify-center align-center py-1"
      >
        <v-btn
          size="x-small"
          variant="text"
          density="comfortable"
          icon="mdi-chevron-right"
          title="Expand filters"
          @click="drawerCollapsed = false"
        />
      </div>
    </template>

    <template v-else>
      <div
        class="select-drawer__header px-3 py-1 d-flex align-center gap-1"
      >
        <v-icon icon="mdi-tune" color="primary" size="16" />
        <span class="text-caption font-weight-medium">Filters</span>
        <v-spacer />
        <v-btn
          size="x-small"
          variant="text"
          density="comfortable"
          icon="mdi-chevron-left"
          title="Collapse filters"
          @click="drawerCollapsed = true"
        />
      </div>

      <v-divider />

      <!-- Collapsible Time range section. Same chevron + primary-
           tinted icon + caption treatment as the edit view so both
           filter drawers read as the same family of controls. -->
      <div
        class="select-drawer__section-header d-flex align-center gap-1 px-3 py-1"
        role="button"
        tabindex="0"
        @click="timeCollapsed = !timeCollapsed"
        @keydown.enter.prevent="timeCollapsed = !timeCollapsed"
        @keydown.space.prevent="timeCollapsed = !timeCollapsed"
      >
        <v-icon
          size="16"
          :icon="timeCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-down'"
        />
        <v-icon icon="mdi-calendar-range" color="primary" size="16" />
        <span class="text-caption font-weight-medium">Time range</span>
      </div>
      <div v-show="!timeCollapsed" class="select-drawer__section px-3 pt-2 pb-3">
        <DataVisTimeFilters />
      </div>

      <v-divider />

      <!-- Collapsible Datastream filters section. -->
      <div
        class="select-drawer__section-header d-flex align-center gap-1 px-3 py-1"
        role="button"
        tabindex="0"
        @click="filtersCollapsed = !filtersCollapsed"
        @keydown.enter.prevent="filtersCollapsed = !filtersCollapsed"
        @keydown.space.prevent="filtersCollapsed = !filtersCollapsed"
      >
        <v-icon
          size="16"
          :icon="filtersCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-down'"
        />
        <v-icon icon="mdi-filter-variant" color="primary" size="16" />
        <span class="text-caption font-weight-medium">Datastream filters</span>
      </div>
      <div
        v-show="!filtersCollapsed"
        class="select-drawer__section px-3 pt-2 pb-2"
      >
        <DatastreamFilters />
      </div>

      <!-- Drag grip pinned to the drawer's right edge. Listens on
           `window` during the drag (via `useResizable`) so the
           gesture keeps tracking after the pointer leaves the
           4-px hit target. -->
      <div
        class="select-drawer__grip"
        :class="{ 'select-drawer__grip--active': dragging }"
        title="Drag to resize"
        @mousedown="startDrag"
      />
    </template>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import DataVisTimeFilters from '@/components/VisualizeData/DataVisTimeFilters.vue'
import DatastreamFilters from '@/components/VisualizeData/DatastreamFilters.vue'
import { useResizable, usePersistedFlag } from '@/composables/useResizable'

// Persisted layout: drawer width, whole-drawer collapse, and
// per-section collapse flags. Keyed under `qc:selectLayout:*` so
// the filter drawer's state survives reloads alongside the edit
// view's `qc:editorLayout:*` preferences.
const { size: drawerWidth, onStart: startDrag, dragging } = useResizable({
  initial: 320,
  min: 240,
  max: 560,
  storageKey: 'qc:selectLayout:drawerWidth',
})
const drawerCollapsed = usePersistedFlag(
  'qc:selectLayout:drawerCollapsed',
  false
)
const timeCollapsed = usePersistedFlag(
  'qc:selectLayout:timeCollapsed',
  false
)
const filtersCollapsed = usePersistedFlag(
  'qc:selectLayout:filtersCollapsed',
  false
)
</script>

<style scoped>
.select-drawer :deep(.v-navigation-drawer__content) {
  overflow-x: hidden;
  /* Leave room for the grip at the right edge so content under
     4px of it doesn't receive accidental clicks. */
  padding-right: 0;
}

.select-drawer__bar,
.select-drawer__header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 32px;
}

/* Section header — same treatment as the edit view's
   `.edit-view__section-header` so the two filter/data drawers
   read as a family. Clickable row with subtle hover tint and
   cursor hint. */
.select-drawer__section-header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  cursor: pointer;
  min-height: 28px;
}
.select-drawer__section-header:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
}
.select-drawer__section-header:focus {
  outline: none;
  background-color: rgba(var(--v-theme-primary), 0.08);
}

.select-drawer__section {
  min-width: 0;
}

/* Grip at the drawer's right edge. Positioned absolutely so it
   doesn't disturb the drawer's own layout; centre rule tints
   primary on hover / while dragging for visibility. */
.select-drawer__grip {
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  width: 4px;
  cursor: col-resize;
  user-select: none;
  z-index: 3;
}
.select-drawer__grip::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 1px;
  width: 2px;
  background: rgba(var(--v-theme-on-surface), 0.08);
}
.select-drawer__grip:hover::after,
.select-drawer__grip--active::after {
  background: rgba(var(--v-theme-primary), 0.55);
}
</style>
