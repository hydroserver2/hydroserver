<template>
  <v-menu
    v-model="open"
    :close-on-content-click="false"
    location="bottom end"
    offset="6"
  >
    <template #activator="{ props: menuProps }">
      <v-btn
        v-if="isEditing"
        v-bind="menuProps"
        size="small"
        :variant="showSourceContext ? 'tonal' : 'text'"
        :color="showSourceContext ? 'primary' : undefined"
        :prepend-icon="
          showSourceContext ? 'mdi-calendar-range' : 'mdi-eye-off-outline'
        "
        data-testid="time-range-btn"
        :data-context-on="showSourceContext"
        :title="
          showSourceContext
            ? `Context range: ${rangeLabel} around the session`
            : `Context range: ${rangeLabel} around the session. The grey source context is hidden.`
        "
      >
        Context &middot; {{ rangeLabel }}
      </v-btn>
      <v-btn
        v-else
        v-bind="menuProps"
        size="small"
        variant="tonal"
        color="primary"
        prepend-icon="mdi-calendar-range"
        data-testid="time-range-btn"
        :title="`Time range: ${rangeLabel}`"
      >
        Time range &middot; {{ rangeLabel }}
      </v-btn>
    </template>
    <v-card width="300" class="pa-3" data-testid="time-range-menu">
      <v-switch
        v-if="isEditing"
        data-testid="context-toggle"
        :model-value="showSourceContext"
        color="primary"
        density="compact"
        hide-details
        inset
        class="mb-2"
        @update:model-value="setShowSourceContext(!!$event)"
      >
        <template #label>
          <span class="d-inline-flex align-center ga-2">
            <span
              class="context-swatch"
              :style="{ backgroundColor: SOURCE_CONTEXT_COLOR }"
            />
            Show source context
          </span>
        </template>
      </v-switch>
      <DataVisTimeFilters
        v-if="isEditing"
        :presets="EDITOR_PRESETS"
        description="How much of the source and plotted datastreams to show before and after the session window. Your edits are not reloaded."
      />
      <DataVisTimeFilters v-else />
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
import DataVisTimeFilters from '@/components/VisualizeData/DataVisTimeFilters.vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { SOURCE_CONTEXT_COLOR } from '@/utils/plotting/plotly'
import {
  CUSTOM_PRESET_ID,
  EDITOR_PRESETS,
  findPreset,
} from '@/utils/timeRangePresets'
import { storeToRefs } from 'pinia'
import { computed, ref } from 'vue'

const { qcDatastream, activePresetId, showSourceContext } = storeToRefs(
  useDataVisStore()
)
const { setShowSourceContext } = useDataVisStore()

// With an edit target the range is the Context around the session.
const isEditing = computed(() => !!qcDatastream.value)

const rangeLabel = computed(() =>
  activePresetId.value === CUSTOM_PRESET_ID
    ? 'Custom'
    : (findPreset(activePresetId.value)?.label ?? 'Custom')
)

const open = ref(false)
</script>

<style scoped>
.context-swatch {
  display: inline-block;
  width: 14px;
  height: 3px;
  border-radius: 2px;
}
</style>
