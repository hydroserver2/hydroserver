<template>
  <v-navigation-drawer
    permanent
    rail
    :width="railWidth"
    :rail-width="railWidth"
    class="datavis-rail"
  >
    <div class="flex h-full flex-col items-center gap-3 py-3">
      <v-tooltip
        :text="drawerTooltip"
        location="right"
        :open-delay="0"
        :close-delay="0"
      >
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            icon
            size="large"
            rounded="lg"
            :color="isOpen ? 'primary' : 'grey'"
            :variant="isOpen ? 'tonal' : 'text'"
            :aria-pressed="isOpen"
            aria-label="Toggle filters drawer"
            @click="sidebar.toggle"
          >
            <v-icon :icon="isOpen ? mdiMenuOpen : mdiMenuClose" />
          </v-btn>
        </template>
      </v-tooltip>

      <div class="my-1 h-px w-8 bg-slate-200" />

      <v-tooltip
        :text="plotTooltip"
        location="right"
        :open-delay="0"
        :close-delay="0"
      >
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            icon
            size="large"
            rounded="lg"
            :color="showPlot ? 'primary' : 'grey'"
            :variant="showPlot ? 'tonal' : 'text'"
            :aria-pressed="showPlot"
            aria-label="Toggle plot visibility"
            @click="togglePlot"
          >
            <v-icon :icon="mdiChartLine" />
          </v-btn>
        </template>
      </v-tooltip>

      <v-tooltip
        :text="tableTooltip"
        location="right"
        :open-delay="0"
        :close-delay="0"
      >
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            icon
            size="large"
            rounded="lg"
            :color="showTable ? 'primary' : 'grey'"
            :variant="showTable ? 'tonal' : 'text'"
            :aria-pressed="showTable"
            aria-label="Toggle datastream table visibility"
            @click="toggleTable"
          >
            <v-icon :icon="showTable ? mdiTable : mdiTableOff" />
          </v-btn>
        </template>
      </v-tooltip>
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useDisplay } from 'vuetify'
import { useDataVisStore } from '@/store/dataVisualization'
import { useSidebarStore } from '@/store/useSidebar'
import {
  mdiChartLine,
  mdiMenuClose,
  mdiMenuOpen,
  mdiTable,
  mdiTableOff,
} from '@mdi/js'

const sidebar = useSidebarStore()
const { isOpen } = storeToRefs(sidebar)
const { showPlot, showTable } = storeToRefs(useDataVisStore())
const { xs } = useDisplay()
const railWidth = computed(() => (xs.value ? 56 : 64))

const drawerTooltip = computed(() =>
  isOpen.value ? 'Hide filters panel' : 'Show filters panel'
)
const plotTooltip = computed(() => (showPlot.value ? 'Hide plot' : 'Show plot'))
const tableTooltip = computed(() =>
  showTable.value ? 'Hide datastreams table' : 'Show datastreams table'
)

const togglePlot = () => {
  if (showPlot.value) {
    if (!showTable.value) showTable.value = true
    showPlot.value = false
    return
  }
  showPlot.value = true
}

const toggleTable = () => {
  if (showTable.value) {
    if (!showPlot.value) showPlot.value = true
    showTable.value = false
    return
  }
  showTable.value = true
}
</script>

<style scoped>
.datavis-rail {
  z-index: 20;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
}
</style>
