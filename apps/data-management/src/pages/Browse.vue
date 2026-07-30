<template>
  <div class="browse-page">
    <BrowseFilterTool
      class="browse-filter-overlay"
      :things="things"
      :things-loaded="loaded"
      :selected-site-id="selectedThingId"
      :show-register-site="hs.session.isAuthenticated"
      :can-register-site="canRegisterSite"
      @filter="updateFilteredThings"
      @select-site="selectedThingId = $event"
      @color-settings="markerColorSettings = $event"
      @register-site="openSiteRegistration"
    />
    <OpenLayersMap
      v-if="loaded"
      class="browse-map"
      selectable
      :things="filteredThings"
      :fit-padding="mapFitPadding"
      :selected-thing-id="selectedThingId"
      :color-mode="markerColorSettings.mode"
      :color-key="markerColorSettings.key"
      :color-labels="markerColorSettings.labels"
      @select="selectedThingId = $event"
    />
    <FullScreenLoader v-else loading-text="Loading map..." />

    <v-dialog v-model="showSiteForm" width="60rem" :persistent="false">
      <SiteForm
        v-if="registrationWorkspaceId"
        :workspace-id="registrationWorkspaceId"
        @close="showSiteForm = false"
        @site-created="loadThings"
      >
        <template #workspace>
          <v-card-text class="pb-2">
            <v-select
              v-model="registrationWorkspaceId"
              data-testid="registration-workspace-select"
              :items="creatableWorkspaces"
              item-title="name"
              item-value="id"
              label="Register site in workspace"
              hide-details
            />
          </v-card-text>
        </template>
      </SiteForm>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import OpenLayersMap from '@/components/Maps/OpenLayersMap.vue'
import BrowseFilterTool from '@/components/Browse/BrowseFilterTool.vue'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
import SiteForm from '@/components/Site/SiteForm.vue'
import hs, { PermissionAction, PermissionResource } from '@hydroserver/client'
import type { ThingSiteSummary } from '@hydroserver/client'
import { useWorkspaceStore } from '@/store/workspaces'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'

const desktopMapFitPadding: [number, number, number, number] = [44, 88, 96, 400]
const compactMapFitPadding: [number, number, number, number] = [72, 48, 72, 48]

const workspaceStore = useWorkspaceStore()
const { workspaces, selectedWorkspace } = storeToRefs(workspaceStore)
const { setWorkspaces } = workspaceStore
const { hasPermission } = useWorkspacePermissions()

const things = ref<ThingSiteSummary[]>([])
const filteredThings = ref<ThingSiteSummary[]>([])
const selectedThingId = ref<string>()
const markerColorSettings = ref<MarkerColorSettings>({
  mode: 'none',
  key: '',
  labels: {},
})
const loaded = ref(false)
const isCompactMapViewport = ref(false)
const showSiteForm = ref(false)
const registrationWorkspaceId = ref('')

interface MarkerColorSettings {
  mode: 'none' | 'workspace' | 'siteType' | 'metadata'
  key: string
  labels: Record<string, string>
}

const creatableWorkspaces = computed(() =>
  workspaces.value.filter((workspace) =>
    hasPermission(PermissionResource.Thing, PermissionAction.Create, workspace)
  )
)
const canRegisterSite = computed(() => creatableWorkspaces.value.length > 0)
const mapFitPadding = computed<[number, number, number, number]>(() =>
  isCompactMapViewport.value ? compactMapFitPadding : desktopMapFitPadding
)

let compactMapQuery: MediaQueryList | undefined

const updateCompactMapViewport = (event?: MediaQueryListEvent) => {
  isCompactMapViewport.value =
    event?.matches ?? compactMapQuery?.matches ?? false
}

const updateFilteredThings = (updatedThings: ThingSiteSummary[]) => {
  filteredThings.value = updatedThings
  if (
    selectedThingId.value &&
    !updatedThings.some((thing) => thing.id === selectedThingId.value)
  ) {
    selectedThingId.value = undefined
  }
}

const loadThings = async () => {
  const res = await hs.things.listSiteSummaries()
  filteredThings.value = things.value = res.ok ? res.data : []
}

const loadAssociatedWorkspaces = async () => {
  if (!hs.session.isAuthenticated || workspaces.value.length) return

  try {
    const associatedWorkspaces = await hs.workspaces.listAllItems({
      is_associated: true,
      expand_related: true,
    })
    setWorkspaces(associatedWorkspaces)
  } catch (error) {
    console.error('Error fetching associated workspaces', error)
  }
}

const openSiteRegistration = () => {
  if (!canRegisterSite.value) return

  registrationWorkspaceId.value =
    creatableWorkspaces.value.find(
      (workspace) => workspace.id === selectedWorkspace.value?.id
    )?.id ?? creatableWorkspaces.value[0].id
  showSiteForm.value = true
}

onMounted(async () => {
  compactMapQuery = window.matchMedia('(max-width: 700px)')
  updateCompactMapViewport()
  compactMapQuery.addEventListener('change', updateCompactMapViewport)

  await Promise.all([loadThings(), loadAssociatedWorkspaces()])

  await new Promise((r) => setTimeout(r, 100))
  loaded.value = true
})

onBeforeUnmount(() => {
  compactMapQuery?.removeEventListener('change', updateCompactMapViewport)
})
</script>

<style scoped>
.browse-page {
  position: relative;
  height: calc(100dvh - var(--v-layout-top, 0px));
  min-height: 520px;
  overflow: hidden;
}

.browse-map {
  width: 100%;
  height: 100%;
}

.browse-filter-overlay {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 1000;
}

@media (max-width: 700px) {
  .browse-filter-overlay {
    inset: 0;
  }

  .browse-filter-overlay:not(.browse-filter-tool--expanded) {
    inset: 12px auto auto 12px;
  }
}
</style>
