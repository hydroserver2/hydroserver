<template>
  <v-navigation-drawer permanent rail class="bg-navbar">
    <v-list-item
      class="pa-2 d-flex justify-center"
      role="link"
      aria-label="Home"
      @click="guardExit(goHome)"
    >
      <v-img :src="HydroServerIcon" width="28" height="28" alt="Home" />
    </v-list-item>

    <v-divider />

    <v-list density="compact" nav>
      <v-tooltip
        v-for="item in items"
        :key="item.title"
        location="right"
        :open-delay="400"
      >
        <template #activator="{ props: tipProps }">
          <v-list-item
            v-bind="tipProps"
            class="nav-rail__item"
            color="primary"
            :prepend-icon="item.icon"
            :value="item.title"
            :active="currentView === item.title"
            :disabled="item.title === 'Edit' && !qcDatastream"
            :data-testid="`nav-rail-item-${item.title.toLowerCase()}`"
            @click="guardExit(() => onRailItemClicked(item.title as DrawerType))"
          />
        </template>
        <span v-if="item.title === 'Edit' && !qcDatastream">
          Edit: select a datastream for quality control before navigating here.
        </span>
        <span v-else>{{ item.title }}</span>
      </v-tooltip>
    </v-list>

    <template #append>
      <v-divider />
      <v-list density="compact" nav>
        <PerformanceCalibration />
        <v-tooltip location="right" :open-delay="400">
          <template #activator="{ props: tipProps }">
            <v-list-item
              v-bind="tipProps"
              prepend-icon="mdi-view-grid-outline"
              @click.prevent="guardExit(onSwitchWorkspace)"
            />
          </template>
          <span>
            <template v-if="selectedWorkspace">
              Workspace: {{ selectedWorkspace.name }} · click to switch
            </template>
            <template v-else>Select a workspace</template>
          </span>
        </v-tooltip>
        <v-tooltip location="right" :open-delay="400">
          <template #activator="{ props: tipProps }">
            <v-list-item
              v-bind="tipProps"
              prepend-icon="mdi-logout"
              @click.prevent="guardExit(onLogout)"
            />
          </template>
          <span>Log out</span>
        </v-tooltip>
      </v-list>
    </template>
  </v-navigation-drawer>

  <SelectDrawer v-if="isDrawerOpen && selectedDrawer === DrawerType.Select" />

  <v-dialog v-model="showExitConfirm" max-width="520" persistent>
    <v-card rounded="lg">
      <div class="d-flex align-center ga-3 px-6 pt-5 pb-2">
        <v-avatar color="warning" variant="tonal" size="40">
          <v-icon icon="mdi-alert-outline" size="22" />
        </v-avatar>
        <div class="d-flex flex-column">
          <div class="text-title-large font-weight-bold">Unsaved edits</div>
          <div class="text-body-small text-medium-emphasis">
            {{ editCount }} pending change{{ editCount === 1 ? '' : 's' }} in
            the editor
          </div>
        </div>
      </div>
      <v-card-text class="text-body-medium pt-2 pb-4 px-6">
        Save your edits before leaving, or discard them to continue. Discarded
        edits cannot be recovered.
      </v-card-text>
      <v-divider />
      <v-card-actions class="d-flex align-center ga-2 px-4 py-3">
        <v-btn variant="text" :disabled="isBusy" @click="cancelExit">
          Cancel
        </v-btn>
        <v-spacer />
        <v-btn
          color="error"
          variant="tonal"
          prepend-icon="mdi-delete-outline"
          :disabled="isBusy"
          :loading="isBusy && exitAction === 'discard'"
          @click="discardAndContinue"
        >
          Discard
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          prepend-icon="mdi-content-save-outline"
          :disabled="isBusy"
          :loading="isBusy && exitAction === 'save'"
          @click="saveAndContinue"
        >
          Save &amp; continue
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import HydroServerIcon from '@/assets/favicon-32x32.png'
import SelectDrawer from '@/components/Navigation/SelectDrawer.vue'
import PerformanceCalibration from '@/components/Navigation/PerformanceCalibration.vue'
import { useUIStore, DrawerType } from '@/store/userInterface'
import { Snackbar } from '@uwrl/qc-utils'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import router from '@/router/router'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'
import { usePlotlyStore } from '@/store/plotly'
import { useQcSubmission } from '@/composables/useQcSubmission'
import { useDataSelection } from '@/composables/useDataSelection'

const { onRailItemClicked } = useUIStore()
const { selectedDrawer, isDrawerOpen, currentView } = storeToRefs(useUIStore())
const { resetState, refreshGraphSeriesArray } = useDataVisStore()
const { qcDatastream, qcDatastreamId } = storeToRefs(useDataVisStore())
const { hs } = storeToRefs(useHydroServer())
const workspaceStore = useWorkspaceStore()
const { selectedWorkspace } = storeToRefs(workspaceStore)
const { editHistory, isUpdating, selectedSeries } = storeToRefs(usePlotlyStore())
const { redraw } = usePlotlyStore()
const { submitQcEdits } = useQcSubmission()
const { clearSelected } = useDataSelection()

const editCount = computed(() => editHistory.value?.length ?? 0)
const hasUnsavedEdits = computed(
  () => currentView.value === DrawerType.Edit && editCount.value > 0
)

const showExitConfirm = ref(false)
const exitAction = ref<'save' | 'discard' | null>(null)
const isBusy = ref(false)
let pendingAction: (() => void | Promise<void>) | null = null

function guardExit(action: () => void | Promise<void>) {
  if (hasUnsavedEdits.value) {
    pendingAction = action
    showExitConfirm.value = true
  } else {
    action()
  }
}

function cancelExit() {
  if (isBusy.value) return
  pendingAction = null
  showExitConfirm.value = false
}

async function saveAndContinue() {
  if (isBusy.value) return
  isBusy.value = true
  exitAction.value = 'save'
  try {
    await submitQcEdits()
    const next = pendingAction
    pendingAction = null
    showExitConfirm.value = false
    await next?.()
  } finally {
    isBusy.value = false
    exitAction.value = null
  }
}

async function discardAndContinue() {
  if (isBusy.value) return
  isBusy.value = true
  exitAction.value = 'discard'
  isUpdating.value = true
  try {
    // In-place clear: reassigning `history = []` detaches the editHistory ref.
    if (selectedSeries.value) selectedSeries.value.data.history.length = 0
    await refreshGraphSeriesArray()
    await selectedSeries.value?.data.reload()
    await clearSelected({ recordHistory: false })
    await redraw()
    const next = pendingAction
    pendingAction = null
    showExitConfirm.value = false
    await next?.()
  } finally {
    isUpdating.value = false
    isBusy.value = false
    exitAction.value = null
  }
}

function goHome() {
  resetState()
  qcDatastreamId.value = null
  currentView.value = DrawerType.Select
  selectedDrawer.value = DrawerType.Select
  isDrawerOpen.value = true
  window.location.assign('/')
}

const items = ref([
  { title: 'Select', icon: 'mdi-cursor-default-click-outline' },
  { title: 'Edit', icon: 'mdi-pencil' },
])

async function onLogout() {
  await hs.value.session.logout()
  workspaceStore.clearSelection()
  Snackbar.info('You have logged out')
  window.location.assign('/login')
}

async function onSwitchWorkspace() {
  // Navigate BEFORE mutating refs: VisualizeData's deep watcher syncs
  // filters to router.replace, racing our push and stranding the user.
  // `switch=1` prevents the Workspaces picker from auto-redirecting back.
  await router.push({ name: 'Workspaces', query: { switch: '1' } })
  qcDatastreamId.value = null
  currentView.value = DrawerType.Select
  selectedDrawer.value = DrawerType.Select
  isDrawerOpen.value = true
}
</script>

<style scoped>
.nav-rail__item.v-list-item--active {
  background-color: rgba(var(--v-theme-primary), 0.14);
}

.nav-rail__item.v-list-item--active::before {
  content: '';
  position: absolute;
  inset: 4px auto 4px 0;
  width: 3px;
  border-radius: 0 2px 2px 0;
  background-color: rgb(var(--v-theme-primary));
}
</style>
