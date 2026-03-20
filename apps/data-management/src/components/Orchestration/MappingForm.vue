<template>
  <v-row align="center">
    <v-col cols="auto">
      <v-card-title class="text-subtitle-1 text-medium-emphasis px-0 mb-1"
        >Source to target mapping</v-card-title
      >
    </v-col>
    <v-col class="pl-0">
      <v-icon
        :icon="mdiHelpCircleOutline"
        @click="showHelp = !showHelp"
        color="grey"
        small
      />
    </v-col>

    <v-spacer />

    <v-col cols="auto">
      <v-btn-add
        variant="text"
        class="mr-2"
        @click="onAddMapping"
        color="secondary-darken-1"
      >
        Add row
      </v-btn-add>
    </v-col>
  </v-row>

  <div v-if="showHelp" class="mb-4">
    A source to target mapping allows you to map a unique source identifier to a
    unique target identifier. These identifiers depend on the task type, but can
    be column names or indexes for CSV, object keys for JSON, etc. HydroServer
    uses the datastream's ID as its identifier.
  </div>
  <div v-if="showHelp" class="mb-4">
    Adding a data transformation will allow you to apply a unit conversion or
    rating curve to each data point for a mapping. Optionally, you can also save
    the raw data to a separate datastream. Configuration details for this step
    will be available on the Task Form after creating this data connection.
  </div>

  <v-expansion-panels
    v-model="openPanels"
    multiple
    elevation="1"
    variant="inset"
  >
    <v-expansion-panel
      v-for="(m, mi) in task.mappings ?? []"
      :key="mi"
      density="compact"
      class="bg-grey-lighten-4"
    >
      <v-expansion-panel-title
        :hide-actions="true"
        expand-icon=""
        density="compact"
        class="px-2"
      >
        <template #default="{ expanded }">
          <v-icon
            class="mx-2 chevron-icon"
            :icon="expanded ? mdiChevronDown : mdiChevronRight"
          />
          <span>{{ m.sourceIdentifier || 'New source' }}</span>
          <v-icon
            :icon="mdiArrowRight"
            size="16"
            class="mx-2"
            color="green-lighten-2"
          />
          <span class="text-medium-emphasis">
            {{ targetsCount(m) }}
          </span>
          <v-spacer />
          <v-btn
            icon
            variant="text"
            color="error"
            :title="`Remove ${m.sourceIdentifier || 'source'}`"
            @click.stop="onRemoveMapping(mi)"
          >
            <v-icon :icon="mdiTrashCanOutline" size="18" />
          </v-btn>
        </template>
      </v-expansion-panel-title>

      <v-expansion-panel-text class="pa-2">
        <v-text-field
          v-model="m.sourceIdentifier"
          label="Source identifier (CSV column name/index or JSON key)"
          placeholder="e.g., water_level_ft"
          density="comfortable"
          variant="outlined"
          class="mt-3 mx-2"
        />

        <MappingPathCards v-model:mapping="task.mappings[mi]" />

        <v-btn
          size="small"
          variant="text"
          color="secondary-darken-1"
          :prepend-icon="mdiSourceBranchPlus"
          @click="addPath(m)"
        >
          Add path
        </v-btn>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import MappingPathCards from './MappingPathCards.vue'
import { Mapping, Task } from '@hydroserver/client'
import {
  mdiArrowRight,
  mdiChevronDown,
  mdiChevronRight,
  mdiHelpCircleOutline,
  mdiSourceBranchPlus,
  mdiTrashCanOutline,
} from '@mdi/js'

const task = defineModel<Task>('task', { required: true })

const showHelp = ref(false)
const openPanels = ref<number[]>([])

function onAddMapping() {
  task.value.mappings.push({
    sourceIdentifier: '',
    paths: [{ targetIdentifier: '', dataTransformations: [] }],
  })
  openPanels.value = [task.value.mappings.length - 1]
}
function onRemoveMapping(index: number) {
  task.value.mappings.splice(index, 1)
  openPanels.value = openPanels.value
    .filter((i) => i !== index)
    .map((i) => (i > index ? i - 1 : i))
}

const targetsCount = (m: Mapping) => {
  const n = m.paths?.length ?? 0
  return `${n} target${n === 1 ? '' : 's'}`
}

function addPath(m: Mapping) {
  m.paths.push({ targetIdentifier: '', dataTransformations: [] })
}

onMounted(() => {})
</script>

<style scoped>
.chevron-icon svg {
  stroke-width: 1.5; /* thinner lines */
}
</style>
