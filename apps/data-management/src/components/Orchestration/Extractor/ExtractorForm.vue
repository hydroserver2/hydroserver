<template>
  <v-form ref="localForm" v-model="isValid" validate-on="input">
    <v-card class="mt-4" color="brown-darken-4" variant="outlined" rounded="lg">
      <v-toolbar title="Source" color="brown" />

      <v-row align="center" class="px-2 pt-0">
        <v-col cols="auto" class="pr-0">
          <v-card-item><v-card-title>URL</v-card-title></v-card-item>
        </v-col>
        <v-col class="pl-0">
          <v-icon
            :icon="mdiHelpCircleOutline"
            @click="showUrlHelp = !showUrlHelp"
            color="grey"
            size="small"
          />
        </v-col>
      </v-row>

      <v-card-text v-if="showUrlHelp" class="pt-0">
        Specify the HTTP endpoint to fetch data from. Use
        <code>{placeholders}</code> for dynamic values:
        <ul class="ma-4">
          <li>
            <strong>Per-task variables</strong> — supplied individually for
            each task.
          </li>
          <li>
            <strong>Latest observation timestamp</strong> — last ingested
            timestamp for a datastream.
          </li>
          <li>
            <strong>Run-time variables</strong> — computed at run time.
          </li>
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
            class="mb-2 align-center"
          >
            <v-col cols="auto">
              <v-chip
                variant="text"
                density="compact"
                :prepend-icon="mdiCodeBraces"
              >
                {{ variable.name }}
              </v-chip>
            </v-col>
            <v-col>
              <v-radio-group v-model="variable.type" inline hide-details>
                <v-radio label="Define per task" value="per_task" />
                <v-radio
                  label="Latest observation timestamp"
                  value="latest_observation_timestamp"
                />
                <v-radio label="Run time" value="run_time" />
              </v-radio-group>
            </v-col>
            <v-col v-if="variable.type !== 'per_task'" cols="12" md="4">
              <v-text-field
                v-model="variable.timestampFormat"
                label="Timestamp format (optional)"
                hint="strftime format string"
                density="compact"
                clearable
                hide-details
              />
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
import { VForm } from 'vuetify/lib/components/index.mjs'
import { mdiCodeBraces, mdiHelpCircleOutline } from '@mdi/js'

const localForm = ref<VForm>()
const isValid = ref(true)
const showUrlHelp = ref(false)

async function validate() {
  await localForm.value?.validate()
  return isValid.value
}

defineExpose({ validate })

const { dataConnection } = storeToRefs(useDataConnectionStore())

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
</script>
