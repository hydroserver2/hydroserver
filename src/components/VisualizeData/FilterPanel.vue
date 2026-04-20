<template>
  <v-expansion-panel elevation="0" class="filter-panel">
    <v-expansion-panel-title class="d-flex align-center">
      <template #default>
        <v-icon :icon="icon" size="16" color="primary" class="mr-2" />
        <span class="flex-grow-1 text-truncate">{{ label }}</span>
        <v-chip
          v-if="selectedCount"
          size="x-small"
          color="primary"
          variant="tonal"
          class="ml-2"
        >
          {{ selectedCount }}
        </v-chip>
        <v-chip
          v-else
          size="x-small"
          variant="tonal"
          color="grey-lighten-1"
          class="ml-2"
        >
          {{ total }}
        </v-chip>
      </template>
    </v-expansion-panel-title>

    <v-expansion-panel-text>
      <!-- Hide the search input on small categories — typing to narrow
           a list of <10 items is more friction than just scanning it.
           The threshold matches the chip shown in the panel header. -->
      <v-text-field
        v-if="total >= 10"
        :model-value="search"
        @update:model-value="$emit('update:search', $event ?? '')"
        clearable
        prepend-inner-icon="mdi-magnify"
        placeholder="Search…"
        hide-details
        density="compact"
        variant="outlined"
        class="mb-2"
      />
      <slot />
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>

<script setup lang="ts">
defineProps<{
  icon: string
  label: string
  total: number
  selectedCount: number
  search: string
}>()

defineEmits<{
  (e: 'update:search', value: string): void
}>()
</script>

<style scoped>
.filter-panel {
  border: none !important;
}
</style>
