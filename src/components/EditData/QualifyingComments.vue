<template>
  <v-card>
    <v-card-title>Qualifying comments</v-card-title>
    <v-card-subtitle>
      <span class="selected-count-badge">
        <v-icon icon="mdi-vector-selection" size="14" />
        {{ selectedData?.length ?? 0 }} point{{
          selectedData?.length === 1 ? '' : 's'
        }}
        selected
      </span>
    </v-card-subtitle>

    <v-card-text>
      <div class="text-caption text-medium-emphasis mb-2">
        Pick one or more qualifier flags to apply.
      </div>

      <v-autocomplete
        v-model="selectedQualifierIds"
        :items="qualifierItems"
        item-title="label"
        item-value="id"
        label="Qualifiers"
        multiple
        chips
        closable-chips
        density="comfortable"
        variant="outlined"
        :disabled="!selectedData?.length"
      />

      <div class="d-flex justify-end mt-n2 mb-3">
        <v-btn
          size="x-small"
          variant="text"
          prepend-icon="mdi-plus"
          @click="openNewQualifier = true"
        >
          New qualifier
        </v-btn>
      </div>

      <div v-if="existingAtSelection.length">
        <div class="text-caption font-weight-medium mb-1">
          Already applied
        </div>
        <div class="d-flex flex-wrap gap-1">
          <v-chip
            v-for="code in existingAtSelection"
            :key="code"
            size="x-small"
            color="primary"
            variant="tonal"
          >
            {{ code }}
          </v-chip>
        </div>
      </div>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="!canApply"
        @click="onApply"
      >
        Apply
      </v-btn>
    </v-card-actions>
  </v-card>

  <v-dialog v-model="openNewQualifier" max-width="450">
    <v-card>
      <v-card-title>New qualifier</v-card-title>
      <v-divider />
      <v-card-text>
        <v-text-field
          v-model="newCode"
          label="Code"
          density="comfortable"
          variant="outlined"
          :rules="[(v: string) => !!v?.trim() || 'Code is required']"
        />
        <v-text-field
          v-model="newDescription"
          label="Description"
          density="comfortable"
          variant="outlined"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="closeNewQualifier">Cancel</v-btn-cancel>
        <v-btn
          color="primary"
          :disabled="!newCode.trim()"
          @click="onCreateQualifier"
        >Create</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import { useQualifierStore } from '@/store/qualifiers'
import { useUserStore } from '@/store/user'
import { useDataSelection } from '@/composables/useDataSelection'
import { handleNewPlot } from '@/utils/plotting/plotly'

const emit = defineEmits(['close'])

const { selectedData, qcDatastream } = storeToRefs(useDataVisStore())
const { plotlyRef } = storeToRefs(usePlotlyStore())
const { updateOptions } = usePlotlyStore()
const { clearSelected } = useDataSelection()

const qualifierStore = useQualifierStore()
const { qualifiers } = storeToRefs(qualifierStore)
const { user } = storeToRefs(useUserStore())

const selectedQualifierIds = ref<string[]>([])
const openNewQualifier = ref(false)
const newCode = ref('')
const newDescription = ref('')

const qualifierItems = computed(() =>
  qualifiers.value.map((q) => ({
    id: q.id,
    label: q.description ? `${q.code} — ${q.description}` : q.code,
  }))
)

const existingAtSelection = computed(() => {
  if (!qcDatastream.value?.id || !selectedData.value?.length) return []
  const codes = new Set<string>()
  for (const i of selectedData.value) {
    const apps = qualifierStore.getApplicationsAtIndex(qcDatastream.value.id, i)
    for (const a of apps) {
      const q = qualifierStore.qualifierById[a.qualifierId]
      if (q) codes.add(q.code)
    }
  }
  return Array.from(codes).sort()
})

const canApply = computed(
  () =>
    !!qcDatastream.value?.id &&
    !!selectedData.value?.length &&
    selectedQualifierIds.value.length > 0
)

const appliedByLabel = computed(() => {
  const u = user.value
  const name = [u?.firstName, u?.lastName].filter(Boolean).join(' ').trim()
  return name || u?.email || 'anonymous'
})

function closeNewQualifier() {
  openNewQualifier.value = false
  newCode.value = ''
  newDescription.value = ''
}

async function onCreateQualifier() {
  const code = newCode.value.trim()
  if (!code) return
  // `createQualifier` is now async — it POSTs to
  // `hs.resultQualifiers` so the code persists on the server for the
  // active workspace.
  const q = await qualifierStore.createQualifier(code, newDescription.value)
  if (!selectedQualifierIds.value.includes(q.id)) {
    selectedQualifierIds.value = [...selectedQualifierIds.value, q.id]
  }
  closeNewQualifier()
}

async function onApply() {
  if (!canApply.value || !qcDatastream.value?.id || !selectedData.value) return

  qualifierStore.applyQualifiers(
    qcDatastream.value.id,
    selectedData.value,
    selectedQualifierIds.value,
    appliedByLabel.value
  )

  selectedQualifierIds.value = []
  await clearSelected()
  // Rebuild the plot so newly-added qualifier band traces are drawn.
  updateOptions()
  if (plotlyRef.value) await handleNewPlot(undefined, { preserveZoom: true })
  emit('close')
}
</script>
