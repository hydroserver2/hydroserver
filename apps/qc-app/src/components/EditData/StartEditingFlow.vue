<template>
  <v-dialog v-model="showChooser" max-width="640">
    <StartEditingDialog
      v-if="chooserSource"
      :source="chooserSource"
      :options="chooserOptions"
      :loading="chooserLoading"
      @edit="onChooserEdit"
      @delete="onChooserDelete"
      @delete-session="onChooserDeleteSession"
      @create="onChooserCreate"
      @cancel="showChooser = false"
    />
  </v-dialog>

  <v-dialog v-model="showCreateDatastream" max-width="560" persistent>
    <v-card v-if="chooserSource" rounded="lg">
      <CreateDatastreamForm
        :key="chooserSource.id"
        :source="chooserSource"
        :processing-levels="processingLevels"
        :sensors="sensors"
        :statuses="statuses"
        :default-processing-level-id="qcPreferences.processingLevelId"
        :on-create-processing-level="onCreateProcessingLevel"
        :permission-error="createPermissionError"
        @cancel="onCreateCancel"
        @confirm="onCreateDatastream"
      />
    </v-card>
  </v-dialog>

  <v-dialog v-model="showWindow" max-width="520" :persistent="isStartingSession">
    <SessionWindowDialog
      v-if="windowTarget"
      :key="windowTarget.key"
      :managed-name="windowTarget.name"
      :source="windowTarget.source"
      :sessions="windowTarget.sessions"
      :loading="isStartingSession"
      @confirm="onWindowConfirm"
      @cancel="onWindowCancel"
    />
  </v-dialog>
</template>

<script setup lang="ts">
/**
 * Row Edit flow: choose a managed datastream of a source (or create the
 * first one), pick a session window when there is no session to continue,
 * then enter the editor.
 */

import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Snackbar } from '@uwrl/qc-utils'
import type { Datastream, QualityControlSession } from '@hydroserver/client'
import CreateDatastreamForm from '@/components/EditData/CreateDatastreamForm.vue'
import SessionWindowDialog from '@/components/EditData/SessionWindowDialog.vue'
import StartEditingDialog from '@/components/EditData/StartEditingDialog.vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { useQcPreferencesStore } from '@/store/qcPreferences'
import { useQcSessionStore } from '@/store/qcSession'
import { useWorkingCopiesStore } from '@/store/workingCopies'
import {
  useCreateManagedDatastream,
  type CreateManagedDatastreamSpec,
} from '@/composables/useCreateManagedDatastream'
import { useEditEntry } from '@/composables/useEditEntry'
import {
  useManagedDatastreams,
  type ManagedDatastreamOption,
} from '@/composables/useManagedDatastreams'
import { useDatastreamMetadata } from '@/composables/useDatastreamMetadata'
import { useProcessingLevels } from '@/composables/useProcessingLevels'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { collectDeletionChain } from '@/utils/sessionGraph'
import type { TimeWindow } from '@/utils/timeRangePresets'

// 'entering': the editor is not open yet. 'resume': it opened with no session.
// 'footer': it is open on committed history.
type WindowOrigin = 'entering' | 'resume' | 'footer'

interface WindowTarget {
  /** New for every target, so the dialog never keeps a previous one's defaults. */
  key: number
  managedId: string
  name: string
  source: Datastream
  sessions: QualityControlSession[]
  origin: WindowOrigin
}

const { qcDatastream, datastreams, processingLevels } =
  storeToRefs(useDataVisStore())
const { addQcHistory, removeManagedDatastream } = useDataVisStore()
const { sourceDatastream, sessions, inProgressSession } =
  storeToRefs(useQcSessionStore())
const qcPreferences = useQcPreferencesStore()
const workingCopies = useWorkingCopiesStore()
const { loadForSource, deleteManaged, deleteSessionChain } =
  useManagedDatastreams()
const { create: createManaged } = useCreateManagedDatastream()
const { createProcessingLevel } = useProcessingLevels()
const { sensors, statuses, load: loadDatastreamMetadata } =
  useDatastreamMetadata()
const { canCreateDatastream, roleName } = useWorkspacePermissions()
const { enterEdit, startSessionOver, leaveEdit } = useEditEntry()

const createPermissionError = computed(() =>
  canCreateDatastream()
    ? ''
    : `Your role on this workspace (${roleName()}) can't create datastreams. Ask a workspace owner for an editor role.`
)

const showChooser = ref(false)
const chooserLoading = ref(false)
const chooserOptions = ref<ManagedDatastreamOption[]>([])
const chooserSource = ref<Datastream | null>(null)
const showCreateDatastream = ref(false)

// The form's method and status lists are only needed once it opens.
watch(showCreateDatastream, (open) => {
  if (open) void loadDatastreamMetadata()
})

const windowTarget = ref<WindowTarget | null>(null)
let windowTargetCount = 0
function openWindow(target: Omit<WindowTarget, 'key'>) {
  windowTarget.value = { ...target, key: ++windowTargetCount }
}
const isStartingSession = ref(false)
const showWindow = computed({
  get: () => !!windowTarget.value,
  // Esc and scrim closes take the same path as Cancel.
  set: (open) => {
    if (!open && !isStartingSession.value) void onWindowCancel()
  },
})

/** Row Edit button: choose a managed datastream, or create the first one. */
async function openFor(source: Datastream) {
  chooserSource.value = source
  chooserOptions.value = []
  chooserLoading.value = true
  try {
    chooserOptions.value = await loadForSource(source.id)
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not load QC datastreams.'
    )
    return
  } finally {
    chooserLoading.value = false
  }
  if (chooserOptions.value.length) showChooser.value = true
  else showCreateDatastream.value = true
}

async function onChooserEdit(option: ManagedDatastreamOption) {
  showChooser.value = false
  const source = chooserSource.value
  if (!source) return
  if (option.sessions.some((s) => s.status === 'in_progress')) {
    await runEnter(option.managed.id)
    return
  }
  openWindow({
    managedId: option.managed.id,
    name: option.managed.name,
    source,
    sessions: option.sessions,
    origin: 'entering',
  })
}

/** Window step for the open editor's target. False when it cannot open. */
function openSessionWindow(origin: 'resume' | 'footer'): boolean {
  const managed = qcDatastream.value
  const source = sourceDatastream.value
  if (!managed || !source) return false
  openWindow({
    managedId: managed.id,
    name: managed.name,
    source,
    sessions: sessions.value,
    origin,
  })
  return true
}

/** Editor footer "New session". */
function openNewSession() {
  openSessionWindow('footer')
}

async function resume(managedId: string) {
  await runEnter(managedId)
}

async function runEnter(managedId: string, window?: TimeWindow) {
  try {
    const result = await enterEdit(managedId, window)
    if (result === 'needs-window' && !openSessionWindow('resume')) {
      // No source to window, so the open editor has nothing to edit.
      await leaveEdit()
      Snackbar.error('Could not load the source datastream for a new session.')
    }
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not open the datastream for editing.'
    )
  }
}

async function onWindowConfirm(window: TimeWindow) {
  const target = windowTarget.value
  if (!target) return
  isStartingSession.value = true
  let pickAgain = false
  try {
    if (target.origin === 'entering') {
      await runEnter(target.managedId, window)
    } else {
      const started = await startSessionOver(window)
      // A plain failure keeps the editor on this target; a superseded one left.
      pickAgain = !started && qcDatastream.value?.id === target.managedId
    }
  } finally {
    isStartingSession.value = false
    // A failed entering start reopens the step with a new target; keep that.
    if (!pickAgain && windowTarget.value === target) windowTarget.value = null
  }
}

async function onWindowCancel() {
  const target = windowTarget.value
  if (!target) return
  windowTarget.value = null
  // A resume without an in-progress session leaves nothing to edit.
  if (target.origin === 'resume' && !inProgressSession.value) {
    await leaveEdit()
  }
}

function onChooserCreate() {
  showChooser.value = false
  showCreateDatastream.value = true
}

// Cancelling create returns to the chooser it was opened from, if any.
function onCreateCancel() {
  showCreateDatastream.value = false
  if (chooserOptions.value.length) showChooser.value = true
}

async function onCreateProcessingLevel(input: {
  code: string
  definition?: string
  explanation?: string
}) {
  try {
    const level = await createProcessingLevel(input)
    // Add to the catalog so it shows in the picker and is immediately valid.
    processingLevels.value = [...processingLevels.value, level]
    Snackbar.success('Processing level added.')
    return level
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not add the processing level.'
    )
    return null
  }
}

async function onCreateDatastream(spec: CreateManagedDatastreamSpec) {
  showCreateDatastream.value = false
  qcPreferences.processingLevelId = spec.processingLevelId
  try {
    const { managedDatastream, history } = await createManaged(spec)
    // Register the new history and datastream so it's hidden from the
    // catalog and resolvable as an edit target without a reload.
    addQcHistory(history)
    datastreams.value = [...datastreams.value, managedDatastream]
    Snackbar.success('Managed datastream created.')
    openWindow({
      managedId: managedDatastream.id,
      name: managedDatastream.name,
      source: spec.source,
      sessions: [],
      origin: 'entering',
    })
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not create the datastream.'
    )
  }
}

async function onChooserDelete(option: ManagedDatastreamOption) {
  try {
    await deleteManaged(option.historyId, option.managed.id)
    removeManagedDatastream(option.historyId, option.managed.id)
    workingCopies.invalidate(option.managed.id)
    chooserOptions.value = chooserOptions.value.filter(
      (o) => o.historyId !== option.historyId
    )
    Snackbar.success('Managed datastream deleted.')
  } catch (e) {
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not delete the managed datastream.'
    )
  }
}

// Only the chosen session and those built on it go; the managed datastream
// and its other commits remain.
async function onChooserDeleteSession(
  option: ManagedDatastreamOption,
  sessionId: string
) {
  try {
    // Same input the confirmation previewed, so the two cannot disagree.
    const deleted = await deleteSessionChain(
      option.historyId,
      collectDeletionChain(option.sessions, sessionId)
    )
    workingCopies.invalidate(option.managed.id)
    const gone = new Set(deleted)
    chooserOptions.value = chooserOptions.value.map((o) =>
      o.historyId === option.historyId
        ? { ...o, sessions: o.sessions.filter((s) => !gone.has(s.id)) }
        : o
    )
    Snackbar.success(
      deleted.length === 1
        ? 'Session deleted.'
        : `${deleted.length} sessions deleted.`
    )
  } catch (e) {
    // Refresh regardless: a partial cascade leaves the chooser's copy wrong.
    if (chooserSource.value) {
      chooserOptions.value = await loadForSource(chooserSource.value.id)
    }
    Snackbar.error(
      e instanceof Error ? e.message : 'Could not delete the session.'
    )
  }
}

defineExpose({ openFor, openNewSession, resume })
</script>
