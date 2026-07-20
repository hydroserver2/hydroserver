<template>
  <v-navigation-drawer permanent :width="88" class="nav-rail">
    <div class="rail-main">
      <button
        class="home-icon-btn"
        aria-label="Home"
        @click="guardExit(goHome)"
      >
        <v-img
          :src="HydroServerIcon"
          width="30"
          height="30"
          alt="HydroServer Icon"
        />
      </button>

      <v-tooltip
        v-for="item in items"
        :key="item.title"
        location="right"
        :open-delay="400"
      >
        <template #activator="{ props: tipProps }">
          <button
            v-bind="tipProps"
            class="rail-btn"
            :class="{
              active: currentView === item.title,
              disabled: item.title === 'Edit' && !qcDatastream,
            }"
            :aria-disabled="item.title === 'Edit' && !qcDatastream"
            :tabindex="item.title === 'Edit' && !qcDatastream ? -1 : 0"
            :style="
              currentView === item.title
                ? {
                    '--accent': 'rgb(var(--v-theme-primary))',
                    '--accent-light': 'rgba(var(--v-theme-primary), 0.14)',
                  }
                : {}
            "
            :data-testid="`nav-rail-item-${item.title.toLowerCase()}`"
            @click="onMainRailItemClicked(item.title as DrawerType)"
          >
            <span
              class="rail-pill"
              :style="
                currentView === item.title
                  ? { background: 'var(--accent-light)' }
                  : {}
              "
            >
              <v-icon
                :icon="item.icon"
                size="22"
                :color="currentView === item.title ? 'primary' : undefined"
              />
            </span>
            <span
              class="rail-label"
              :style="
                currentView === item.title
                  ? { color: 'var(--accent)', fontWeight: 600 }
                  : {}
              "
            >
              {{ item.title }}
            </span>
          </button>
        </template>
        <span v-if="item.title === 'Edit' && !qcDatastream">
          Edit: select a datastream for quality control before navigating here.
        </span>
        <span v-else>{{ item.title }}</span>
      </v-tooltip>
    </div>

    <div class="rail-bottom">
      <PerformanceCalibration rail-button />
      <v-tooltip location="right" :open-delay="400">
        <template #activator="{ props: tipProps }">
          <button
            v-bind="tipProps"
            class="rail-btn rail-btn-secondary"
            @click.prevent="guardExit(onSwitchWorkspace)"
          >
            <span class="rail-pill rail-pill-secondary">
              <v-icon icon="mdi-briefcase-outline" size="22" />
            </span>
            <span class="rail-label">Workspaces</span>
          </button>
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
          <button
            v-bind="tipProps"
            class="rail-btn rail-btn-secondary"
            @click.prevent="guardExit(onLogout)"
          >
            <span class="rail-pill rail-pill-secondary">
              <v-icon icon="mdi-logout" size="22" />
            </span>
            <span class="rail-label">Log out</span>
          </button>
        </template>
        <span>Log out</span>
      </v-tooltip>
    </div>
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
import HydroServerIcon from '@/assets/icon-color-thick.svg'
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
const { editHistory, isUpdating, selectedSeries } =
  storeToRefs(usePlotlyStore())
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

function onMainRailItemClicked(item: DrawerType) {
  if (item === DrawerType.Edit && !qcDatastream.value) return
  guardExit(() => onRailItemClicked(item))
}

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
.nav-rail {
  width: 88px;
  border-right: 1px solid #e8e8e8;
  background: #fafafa;
  flex-shrink: 0;
}

.nav-rail :deep(.v-navigation-drawer__content) {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  overflow: hidden;
}

.rail-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  width: 100%;
}

.home-icon-btn {
  width: 48px;
  height: 48px;
  margin: 0 0 10px;
  border: none;
  border-radius: 14px;
  background: #ffffff;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.18),
    0 1px 2px rgba(0, 0, 0, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    background 0.15s,
    box-shadow 0.15s,
    transform 0.15s;
}

.home-icon-btn:hover {
  background: #f8fbff;
  box-shadow:
    0 2px 6px rgba(0, 0, 0, 0.2),
    0 1px 3px rgba(0, 0, 0, 0.14);
}

.home-icon-btn:active {
  transform: translateY(1px);
}

.rail-bottom {
  margin-top: auto;
  width: 100%;
  padding-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rail-btn,
:deep(.rail-btn) {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  width: 100%;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
}

.rail-btn:hover .rail-pill,
:deep(.rail-btn:hover .rail-pill) {
  background: rgba(0, 0, 0, 0.05);
}

.rail-btn.disabled {
  cursor: default;
  color: #9aa0a6;
}

.rail-btn.disabled:hover .rail-pill {
  background: transparent;
}

.rail-pill,
:deep(.rail-pill) {
  width: 58px;
  height: 32px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background 0.15s;
}

.rail-btn-secondary,
:deep(.rail-btn-secondary) {
  color: #5f6368;
}

.rail-btn-secondary:hover .rail-pill-secondary,
:deep(.rail-btn-secondary:hover .rail-pill-secondary) {
  background: rgba(21, 101, 192, 0.08);
}

.rail-pill-secondary,
:deep(.rail-pill-secondary) {
  background: transparent;
}

.rail-label,
:deep(.rail-label) {
  font-size: 10.5px;
  color: #49454f;
  line-height: 1.2;
  text-align: center;
}
</style>
