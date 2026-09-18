<template>
  <v-navigation-drawer permanent :width="88" class="nav-rail">
    <div class="rail-main">
      <button
        class="home-icon-btn"
        aria-label="Home"
        @click="goHome"
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
          Edit a datastream from its row first.
        </span>
        <span v-else-if="item.title === 'Edit'">Back to the editor</span>
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
            data-testid="nav-rail-workspaces"
            @click.prevent="onSwitchWorkspace"
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
            data-testid="nav-rail-logout"
            @click.prevent="onLogout"
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
</template>

<script setup lang="ts">
import { ref } from 'vue'
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
import { useEditEntry } from '@/composables/useEditEntry'

const { onRailItemClicked } = useUIStore()
const { selectedDrawer, isDrawerOpen, currentView } = storeToRefs(useUIStore())
const { resetState } = useDataVisStore()
const { qcDatastream } = storeToRefs(useDataVisStore())
const { hs } = storeToRefs(useHydroServer())
const workspaceStore = useWorkspaceStore()
const { selectedWorkspace } = storeToRefs(workspaceStore)
const { closeEditor } = useEditEntry()

// Home and log out reload the page, so they end the session themselves.
async function goHome() {
  if (!(await closeEditor())) return
  resetState()
  window.location.assign('/')
}

const items = ref([
  { title: 'Select', icon: 'mdi-cursor-default-click-outline' },
  { title: 'Edit', icon: 'mdi-pencil' },
])

// Switching views never ends the session, so neither item prompts: Select
// keeps the editor's target, session and unsaved edits alive behind it, and
// Edit brings them back.
function onMainRailItemClicked(item: DrawerType) {
  if (item === DrawerType.Edit && !qcDatastream.value) return
  onRailItemClicked(item)
}

async function onLogout() {
  if (!(await closeEditor())) return
  await hs.value.session.logout()
  workspaceStore.clearSelection()
  Snackbar.info('You have logged out')
  window.location.assign('/login')
}

async function onSwitchWorkspace() {
  // In-app navigation goes through the router's leave guard, which asks and
  // tears the session down once the navigation is on its way.
  // `switch=1` prevents the Workspaces picker from auto-redirecting back.
  await router.push({ name: 'Workspaces', query: { switch: '1' } })
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
