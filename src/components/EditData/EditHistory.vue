<template>
  <v-card>
    <v-card-title class="text-body-1">Edit History</v-card-title>

    <v-divider></v-divider>

    <v-card-actions>
      <v-btn
        variant="plain"
        :disabled="editHistory.length === 0 || isUpdating || isSubmitting"
        :loading="isSubmitting"
        @click="onSaveChanges"
        >Save Changes</v-btn
      >
    </v-card-actions>

    <v-dialog v-model="openConfirm" max-width="500">
      <v-card>
        <v-card-title>Submit Quality-Controlled Observations?</v-card-title>
        <v-card-text>
          <p class="mb-2">
            This will
            <strong>overwrite existing server observations</strong> in the
            submitted time range (replace mode). This action cannot be undone.
          </p>
          <p>{{ editHistory.length }} edit(s) pending</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="openConfirm = false">Cancel</v-btn>
          <v-btn color="primary" :loading="isSubmitting" @click="onConfirmSubmit"
            >Submit</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-divider></v-divider>

    <v-card-text>
      <v-timeline side="end" hide-opposite density="compact">
        <v-timeline-item dot-color="green" fill-dot size="small">
          <div class="d-flex align-center">
            <span v-if="selectedSeries?.data.isLoading" class="text-body-1 mr-2"
              >Loading Data...</span
            >
            <span v-else class="text-body-1 mr-2">Data loaded</span>
            <v-spacer></v-spacer>
            <div v-if="selectedSeries?.data.loadingTime">
              {{ formatDuration(selectedSeries?.data.loadingTime) }}
            </div>
            <v-progress-circular
              v-if="selectedSeries?.data.isLoading"
              size="20"
              color="primary"
              indeterminate
              class="ma-2"
            />
            <v-btn
              v-else
              icon="mdi-reload"
              color="blue"
              variant="plain"
              density="comfortable"
              title="Reload at this stage"
              :disabled="isUpdating"
              @click="onReload"
            ></v-btn>
          </div>
        </v-timeline-item>
        <v-timeline-item
          v-for="(entry, index) of editHistory"
          :key="index"
          :size="index < editHistory.length - 1 ? 'small' : 'large'"
          :icon="entry.icon"
          :fill-dot="index < editHistory.length - 1"
          dot-color="blue"
          elevation="4"
        >
          <div class="d-flex align-center">
            <v-expansion-panels>
              <v-expansion-panel>
                <v-expansion-panel-title
                  color="grey-lighten-4 d-flex align-flex-start justify-lg-space-between flex-lg-row flex-column gap-1"
                >
                  <div>{{ entry.method }}</div>
                  <div
                    v-if="entry.duration"
                    class="text-medium-emphasis flex-shrink-0"
                  >
                    {{ formatDuration(entry.duration) }}
                  </div>
                </v-expansion-panel-title>

                <v-expansion-panel-text>
                  <div class="text-caption mb-2">Arguments:</div>
                  <ul class="text-caption px-2">
                    <code>
                      <li v-for="(arg, index) of entry.args" :key="index">
                        {{ arg }}
                      </li>
                    </code>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <div
              class="d-flex ml-2 justify-end align-center"
              style="min-width: 5rem"
            >
              <v-progress-circular
                v-if="entry.isLoading"
                size="20"
                color="primary"
                indeterminate
                class="ma-2"
              />
              <v-btn
                v-else
                icon="mdi-reload"
                color="blue"
                variant="plain"
                density="comfortable"
                :disabled="isUpdating || entry.isLoading"
                title="Reload at this stage"
                @click="onReloadHistory(index)"
              ></v-btn>
              <v-btn
                icon="mdi-close"
                color="red"
                variant="plain"
                density="comfortable"
                title="Undo"
                :disabled="isUpdating"
                @click="onRemoveHistoryItem(index)"
              ></v-btn>
            </div>
          </div>
        </v-timeline-item>
      </v-timeline>

      <v-empty-state
        v-if="editHistory.length === 0"
        icon="mdi-clock"
        text="Edit your data and manage your changes here."
        title="Edit History"
      />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlotlyStore } from '@/store/plotly'
import { useDataSelection } from '@/composables/useDataSelection'
import { useQcSubmission } from '@/composables/useQcSubmission'
import { formatDuration } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'

const { editHistory, selectedSeries, isUpdating, isSubmitting } =
  storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()
const { clearSelected, dispatchSelection } = useDataSelection()
const { submitQcEdits } = useQcSubmission()

const openConfirm = ref(false)

const onSaveChanges = () => {
  openConfirm.value = true
}

const onConfirmSubmit = async () => {
  openConfirm.value = false
  await submitQcEdits()
}

const onReload = async () => {
  isUpdating.value = true

  setTimeout(async () => {
    const { refreshGraphSeriesArray } = useDataVisStore()
    if (selectedSeries.value) {
      selectedSeries.value.data.history = []
    }
    await refreshGraphSeriesArray()
    await selectedSeries.value?.data.reload()
    await clearSelected()
    isUpdating.value = false
    await redraw()
  })
}

const onReloadHistory = async (index: number) => {
  if (index < editHistory.value.length) {
    isUpdating.value = true
    setTimeout(async () => {
      const newSelection = await selectedSeries.value?.data.reloadHistory(index)

      isUpdating.value = false
      await redraw()
      if (newSelection) {
        dispatchSelection(newSelection)
      }
    })
  }
}

const onRemoveHistoryItem = async (index: number) => {
  isUpdating.value = true

  setTimeout(async () => {
    const newSelection =
      await selectedSeries.value?.data.removeHistoryItem(index)

    isUpdating.value = false
    await redraw()
    if (newSelection) {
      dispatchSelection(newSelection)
    }
  })
}

// TODO: ADD CONFIRMATION DIALOGS TO HISTORY OPERATIONS
</script>

<style lang="scss" scoped>
:deep(.v-timeline-item__body) {
  width: 100%;
}

:deep(.v-timeline-item .v-expansion-panel-text) {
  max-height: 15rem;
  overflow-y: auto;
}
</style>
