<template>
  <!-- NOTE: Do not use v-navigation-drawer here.
       In a fullscreen v-dialog overlay it can attach to the app layout and overlap the dialog. -->
  <div class="taskdetails-rail" :style="{ width: `${railWidth}px` }">
    <div class="flex h-full flex-col items-center gap-3 py-3">
      <v-tooltip
        text="Task details"
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
            :color="modelValue === 'details' ? 'primary' : 'grey'"
            :variant="modelValue === 'details' ? 'tonal' : 'text'"
            :aria-pressed="modelValue === 'details'"
            aria-label="Task details"
            @click="emit('update:modelValue', 'details')"
          >
            <v-icon :icon="mdiCardAccountDetails" />
          </v-btn>
        </template>
      </v-tooltip>

      <v-tooltip
        text="Run history"
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
            :color="modelValue === 'runs' ? 'primary' : 'grey'"
            :variant="modelValue === 'runs' ? 'tonal' : 'text'"
            :aria-pressed="modelValue === 'runs'"
            aria-label="Run history"
            @click="emit('update:modelValue', 'runs')"
          >
            <v-icon :icon="mdiHistory" />
          </v-btn>
        </template>
      </v-tooltip>

      <v-tooltip
        text="Mappings"
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
            :color="modelValue === 'mappings' ? 'primary' : 'grey'"
            :variant="modelValue === 'mappings' ? 'tonal' : 'text'"
            :aria-pressed="modelValue === 'mappings'"
            aria-label="Mappings"
            @click="emit('update:modelValue', 'mappings')"
          >
            <v-icon :icon="mdiTable" />
          </v-btn>
        </template>
      </v-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDisplay } from 'vuetify'
import { mdiCardAccountDetails, mdiHistory, mdiTable } from '@mdi/js'

export type TaskDetailsPanel = 'details' | 'runs' | 'mappings'

defineProps<{
  modelValue: TaskDetailsPanel
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: TaskDetailsPanel): void
}>()

const { xs } = useDisplay()
const railWidth = computed(() => (xs.value ? 56 : 64))
</script>

<style scoped>
.taskdetails-rail {
  flex: 0 0 auto;
  position: sticky;
  top: 0;
  height: 100%;
  align-self: stretch;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
}
</style>
