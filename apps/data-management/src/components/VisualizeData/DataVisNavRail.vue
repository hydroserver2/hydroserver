<template>
  <nav class="nav-rail" :style="{ width: `${railWidth}px` }">
    <div class="rail-main">
      <button
        type="button"
        class="rail-btn"
        :class="{ active: isOpen }"
        :style="
          isOpen ? { '--accent': FILTERS_ACCENT, '--accent-light': FILTERS_ACCENT_LIGHT } : {}
        "
        :aria-pressed="isOpen"
        aria-label="Toggle filters drawer"
        :title="drawerTooltip"
        @click="sidebar.toggle"
      >
        <span
          class="rail-pill"
          :style="isOpen ? { background: FILTERS_ACCENT_LIGHT } : {}"
        >
          <v-icon
            :icon="isOpen ? mdiMenuOpen : mdiMenuClose"
            size="22"
            :color="isOpen ? FILTERS_ACCENT : undefined"
          />
        </span>
        <span
          class="rail-label"
          :style="isOpen ? { color: FILTERS_ACCENT, fontWeight: 600 } : {}"
        >
          Filters
        </span>
      </button>

      <div class="rail-divider" />

      <button
        type="button"
        class="rail-btn"
        :class="{ active: showPlot }"
        :style="
          showPlot ? { '--accent': PLOT_ACCENT, '--accent-light': PLOT_ACCENT_LIGHT } : {}
        "
        :aria-pressed="showPlot"
        aria-label="Toggle plot visibility"
        :title="plotTooltip"
        @click="togglePlot"
      >
        <span
          class="rail-pill"
          :style="showPlot ? { background: PLOT_ACCENT_LIGHT } : {}"
        >
          <v-icon
            :icon="mdiChartLine"
            size="22"
            :color="showPlot ? PLOT_ACCENT : undefined"
          />
        </span>
        <span
          class="rail-label"
          :style="showPlot ? { color: PLOT_ACCENT, fontWeight: 600 } : {}"
        >
          Plot
        </span>
      </button>

      <button
        type="button"
        class="rail-btn"
        :class="{ active: showTable }"
        :style="
          showTable
            ? { '--accent': TABLE_ACCENT, '--accent-light': TABLE_ACCENT_LIGHT }
            : {}
        "
        :aria-pressed="showTable"
        aria-label="Toggle datastream table visibility"
        :title="tableTooltip"
        @click="toggleTable"
      >
        <span
          class="rail-pill"
          :style="showTable ? { background: TABLE_ACCENT_LIGHT } : {}"
        >
          <v-icon
            :icon="showTable ? mdiTable : mdiTableOff"
            size="22"
            :color="showTable ? TABLE_ACCENT : undefined"
          />
        </span>
        <span
          class="rail-label"
          :style="showTable ? { color: TABLE_ACCENT, fontWeight: 600 } : {}"
        >
          Table
        </span>
      </button>
    </div>
  </nav>
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

// Accent colors reference the same design tokens (styles/tokens.scss) as
// the Job Orchestration nav rail's accent palette, so the two rails read as
// the same product surface and can't drift into slightly-different blues.
const FILTERS_ACCENT = 'var(--hs-accent-blue)'
const FILTERS_ACCENT_LIGHT = 'var(--hs-accent-blue-bg)'
const PLOT_ACCENT = 'var(--hs-accent-green)'
const PLOT_ACCENT_LIGHT = 'var(--hs-accent-green-bg)'
const TABLE_ACCENT = 'var(--hs-accent-purple)'
const TABLE_ACCENT_LIGHT = 'var(--hs-accent-purple-bg)'

const sidebar = useSidebarStore()
const { isOpen } = storeToRefs(sidebar)
const { showPlot, showTable } = storeToRefs(useDataVisStore())
const { xs } = useDisplay()
const railWidth = computed(() => (xs.value ? 76 : 88))

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
/* Mirrors the nav rail on the Job Orchestration page
   (OrchestrationNavRail.vue) — pill icons with labels underneath, instead of
   the plain icon-only rail this page previously used. */
.nav-rail {
  border-right: 1px solid var(--hs-border);
  background: var(--hs-surface-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--hs-space-16) 0;
  flex-shrink: 0;
  z-index: 20;
}
.rail-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--hs-space-2);
  width: 100%;
}
.rail-divider {
  margin: var(--hs-space-6) 0;
  height: 1px;
  width: 32px;
  background: var(--hs-border);
}
.rail-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--hs-space-4);
  padding: var(--hs-space-8) var(--hs-space-4);
  width: 100%;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
}
.rail-btn:hover .rail-pill {
  background: rgba(0, 0, 0, 0.05);
}
.rail-pill {
  width: 58px;
  height: 32px;
  border-radius: var(--hs-radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background 0.15s;
}
.rail-label {
  font-size: var(--hs-font-2xs);
  color: var(--hs-text-secondary);
  line-height: 1.2;
  text-align: center;
}

@media (max-width: 600px) {
  .rail-pill {
    width: 50px;
  }
}
</style>
