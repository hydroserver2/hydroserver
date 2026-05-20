<template>
  <v-form ref="localForm" v-model="isValid" validate-on="input">
    <v-card color="brown-darken-4" variant="outlined" rounded="lg">
      <v-toolbar color="brown">
        <v-row align="center" class="pt-0">
          <v-col cols="auto" class="pr-0">
            <v-card-item><v-card-title>Source URL</v-card-title></v-card-item>
          </v-col>
          <v-col class="pl-0">
            <v-icon
              :icon="mdiHelpCircleOutline"
              @click="showUrlHelp = !showUrlHelp"
              color="white"
              size="small"
            />
          </v-col>
        </v-row>
      </v-toolbar>

      <v-card-text v-if="showUrlHelp" class="pt-4 pb-0">
        Specify the HTTP endpoint to fetch data from. Use
        <code>{placeholders}</code> for dynamic values:
        <ul class="mt-4 mx-4">
          <li>
            <strong>Per-task variables</strong> — supplied individually for each
            task.
          </li>
          <li>
            <strong>Latest observation timestamp</strong> — last ingested
            timestamp for a datastream.
          </li>
          <li><strong>Run-time variables</strong> — computed at run time.</li>
        </ul>
      </v-card-text>

      <v-card-text>
        <v-row>
          <v-col cols="12">
            <v-text-field
              v-model="dataConnection.sourceUrl"
              label="URL *"
              density="compact"
              rounded="lg"
              :prepend-inner-icon="mdiCodeBraces"
              :rules="rules.requiredAndNoSpaces"
            />
          </v-col>
        </v-row>
      </v-card-text>

      <template v-if="dataConnection.placeholderVariables.length">
        <v-card-item>
          <v-card-title>Placeholder variables</v-card-title>
        </v-card-item>
        <v-card-text>
          <v-row
            v-for="variable in dataConnection.placeholderVariables"
            :key="variable.name"
            class="mb-2"
          >
            <v-col cols="12" md="3">
              <v-chip
                variant="text"
                density="compact"
                :prepend-icon="mdiCodeBraces"
                class="ma-0"
              >
                {{ variable.name }}
              </v-chip>
            </v-col>
            <v-col cols="12" md="3">
              <v-radio-group
                :model-value="getPlaceholderMode(variable)"
                hide-details
                @update:model-value="setPlaceholderMode(variable, $event)"
              >
                <v-radio
                  label="Define this variable per task"
                  value="per_task"
                />
                <v-radio
                  label="Fetch this variable at run-time"
                  value="runtime"
                />
              </v-radio-group>
            </v-col>
            <v-col v-if="getPlaceholderMode(variable) === 'runtime'">
              <v-select
                v-model="variable.type"
                :items="runtimeSourceOptions"
                label="Runtime source *"
                density="compact"
                rounded="lg"
                variant="outlined"
                :rules="rules.required"
                hide-details
                clearable
              />
              <div class="mt-8">
                <TimestampFormat
                  :target="getPlaceholderTimestamp(variable)"
                  color="brown-darken-4"
                />
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </template>
    </v-card>
  </v-form>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useDataConnectionStore } from '@/store/dataConnection'
import { storeToRefs } from 'pinia'
import { rules } from '@/utils/rules'
import TimestampFormat from '../timestamps/TimestampFormat.vue'
import { VForm } from 'vuetify/lib/components/index.mjs'
import { mdiCodeBraces, mdiHelpCircleOutline } from '@mdi/js'
import type { Timestamp } from '@/models/timestamp'

const localForm = ref<VForm>()
const isValid = ref(true)
const showUrlHelp = ref(false)
const runtimeSourceOptions = [
  {
    title: 'Latest observation timestamp',
    value: 'latest_observation_timestamp',
  },
  {
    title: 'Job execution time',
    value: 'run_time',
  },
] as const

async function validate() {
  await localForm.value?.validate()
  return isValid.value
}

defineExpose({ validate })

const { dataConnection } = storeToRefs(useDataConnectionStore())

type PlaceholderVariableForm = {
  name: string
  type?: string | null
  timestampFormat?: string | null
  timestamp?: Timestamp
}

function getPlaceholderMode(variable: { type?: string | null }) {
  return variable.type === 'per_task' ? 'per_task' : 'runtime'
}

function setPlaceholderMode(
  variable: PlaceholderVariableForm,
  mode: string | null
) {
  if (mode === 'per_task') {
    variable.type = 'per_task'
    variable.timestampFormat = null
    delete variable.timestamp
    return
  }

  if (variable.type === 'per_task' || !variable.type) {
    variable.type = 'latest_observation_timestamp'
  }

  getPlaceholderTimestamp(variable)
}

function getPlaceholderTimestamp(variable: PlaceholderVariableForm): Timestamp {
  if (!variable.timestamp) {
    variable.timestamp = {
      format: variable.timestampFormat ? 'custom' : 'naive',
      customFormat: variable.timestampFormat ?? undefined,
      timezoneMode: 'utc',
      timezone: undefined,
    }
  }

  return variable.timestamp
}

function normalizePlaceholderTimestamp(variable: PlaceholderVariableForm) {
  const timestamp = variable.timestamp
  if (!timestamp) return

  variable.timestampFormat =
    timestamp.format === 'custom' ? timestamp.customFormat ?? '' : null
}

watch(
  () => dataConnection.value.sourceUrl,
  (url) => {
    if (!url) {
      dataConnection.value.placeholderVariables = []
      return
    }
    const pattern = /\{([^{}]+)\}/g
    const matched: string[] = []
    let match
    while ((match = pattern.exec(url)) !== null) {
      matched.push(match[1])
    }

    dataConnection.value.placeholderVariables = matched.map((name) => {
      const existing = dataConnection.value.placeholderVariables.find(
        (v) => v.name === name
      )
      return existing ?? { name, type: 'per_task' }
    })
  },
  { immediate: true }
)

watch(
  () => dataConnection.value.placeholderVariables,
  (variables) => {
    for (const variable of variables as PlaceholderVariableForm[]) {
      if (getPlaceholderMode(variable) !== 'runtime') continue
      normalizePlaceholderTimestamp(variable)
    }
  },
  { deep: true, immediate: true }
)
</script>
