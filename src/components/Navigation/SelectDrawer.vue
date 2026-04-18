<template>
  <v-navigation-drawer permanent :width="320" elevation="1" class="select-drawer">
    <div class="select-drawer__header px-3 py-2 d-flex align-center">
      <v-icon icon="mdi-tune" color="primary" size="18" class="mr-2" />
      <span class="text-body-2 font-weight-bold">Filters</span>
    </div>

    <v-divider />

    <div class="select-drawer__section px-3 pt-2 pb-3">
      <div
        class="d-flex align-center text-caption text-medium-emphasis mb-2"
      >
        <v-icon icon="mdi-calendar-range" size="14" class="mr-1" />
        Time range
      </div>
      <DataVisTimeFilters />
    </div>

    <v-divider />

    <div class="select-drawer__section px-3 pt-2 pb-2">
      <div
        class="d-flex align-center text-caption text-medium-emphasis mb-2"
      >
        <v-icon icon="mdi-filter-variant" size="14" class="mr-1" />
        Datastream filters
      </div>
      <DatastreamFilters />
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import DataVisTimeFilters from '@/components/VisualizeData/DataVisTimeFilters.vue'
import DatastreamFilters from '@/components/VisualizeData/DatastreamFilters.vue'
</script>

<style scoped>
.select-drawer :deep(.v-navigation-drawer__content) {
  overflow-x: hidden;
}

.select-drawer__header {
  background-color: rgba(var(--v-theme-primary), 0.04);
  min-height: 36px;
}

.select-drawer__section {
  min-width: 0;
}
</style>
