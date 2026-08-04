<template>
  <div class="browse-page">
    <BrowseFilterTool
      class="browse-filter-overlay"
      :things="things"
      :things-loaded="loaded"
      :selected-site-id="selectedThingId"
      :show-my-sites-filter="hs.session.isAuthenticated"
      :my-workspace-ids="myWorkspaceIds"
      :show-register-site="hs.session.isAuthenticated"
      :can-register-site="canRegisterSite"
      :editable-workspace-ids="editableWorkspaceIds"
      :deletable-workspace-ids="deletableWorkspaceIds"
      @filter="updateFilteredThings"
      @select-site="selectedThingId = $event"
      @color-settings="markerColorSettings = $event"
      @register-site="openSiteRegistration"
      @edit-site="openSiteEditor"
      @delete-site="openSiteDeletion"
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
        @close="closeSiteRegistration"
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

    <v-dialog v-model="showEditSiteForm" width="80rem" :persistent="false">
      <SiteForm
        v-if="editingSite"
        :thing-id="editingSite.id"
        :workspace-id="editingSite.workspaceId"
        @close="closeSiteEditor"
      />
    </v-dialog>

    <v-dialog v-model="showDeleteSiteDialog" width="40rem" :persistent="false">
      <SiteDeleteModal
        v-if="deletingSite"
        :thing="deletingSite"
        @switch-to-access-control="switchToAccessControl"
        @close="closeSiteDeletion"
        @delete="deleteSite"
      />
    </v-dialog>

    <v-dialog
      v-model="showAccessControlDialog"
      width="40rem"
      :persistent="false"
    >
      <SiteAccessControl
        v-if="deletingSite"
        :thing-id="deletingSite.id"
        @close="closeAccessControl"
      />
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
import SiteDeleteModal from '@/components/Site/SiteDeleteModal.vue'
import SiteAccessControl from '@/components/Site/SiteAccessControl.vue'
import hs, { PermissionAction, PermissionResource } from '@hydroserver/client'
import type { Thing, ThingSiteSummary } from '@hydroserver/client'
import { useWorkspaceStore } from '@/store/workspaces'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useThingStore } from '@/store/thing'
import { useTagStore } from '@/store/tags'
import { usePhotosStore } from '@/store/photos'
import { Snackbar } from '@/utils/notifications'

const desktopMapFitPadding: [number, number, number, number] = [44, 88, 96, 400]
const compactMapFitPadding: [number, number, number, number] = [72, 48, 72, 48]

const workspaceStore = useWorkspaceStore()
const { workspaces, selectedWorkspace } = storeToRefs(workspaceStore)
const { thing: storedThing } = storeToRefs(useThingStore())
const { tags, previewTags } = storeToRefs(useTagStore())
const { photos, newPhotos, photosToDelete } = storeToRefs(usePhotosStore())
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
const showEditSiteForm = ref(false)
const editingSite = ref<ThingSiteSummary>()
const showDeleteSiteDialog = ref(false)
const deletingSite = ref<Thing>()
const showAccessControlDialog = ref(false)

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
const hasSitePermission = (
  site: ThingSiteSummary,
  action: PermissionAction
) => {
  const workspace = workspaces.value.find(
    (candidate) => candidate.id === site.workspaceId
  )
  return workspace
    ? hasPermission(PermissionResource.Thing, action, workspace)
    : false
}
const editableWorkspaceIds = computed(() =>
  workspaces.value
    .filter((workspace) =>
      hasPermission(PermissionResource.Thing, PermissionAction.Edit, workspace)
    )
    .map((workspace) => workspace.id)
)
const deletableWorkspaceIds = computed(() =>
  workspaces.value
    .filter((workspace) =>
      hasPermission(
        PermissionResource.Thing,
        PermissionAction.Delete,
        workspace
      )
    )
    .map((workspace) => workspace.id)
)
const myWorkspaceIds = computed(() =>
  workspaces.value.map((workspace) => workspace.id)
)
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

  resetSiteFormContext()
  registrationWorkspaceId.value =
    creatableWorkspaces.value.find(
      (workspace) => workspace.id === selectedWorkspace.value?.id
    )?.id ?? creatableWorkspaces.value[0].id
  showSiteForm.value = true
}

const closeSiteRegistration = async () => {
  showSiteForm.value = false
  resetSiteFormContext()
  await loadThings()
}

const resetSiteFormContext = () => {
  storedThing.value = undefined
  tags.value = []
  previewTags.value = []
  photos.value = []
  newPhotos.value = []
  photosToDelete.value = []
}

const fetchSite = async (site: ThingSiteSummary) => {
  try {
    const thing = await hs.things.getItem(site.id)
    if (thing) return thing
  } catch (error) {
    console.error('Error fetching site', error)
  }

  Snackbar.error(`Unable to load ${site.name}. Please try again.`)
  return null
}

const openSiteEditor = async (site: ThingSiteSummary) => {
  if (!hasSitePermission(site, PermissionAction.Edit)) return

  try {
    const [thing, tagResponse, attachmentResponse] = await Promise.all([
      hs.things.getItem(site.id),
      hs.things.getTags(site.id),
      hs.things.getAttachments(site.id),
    ])
    if (!thing || !tagResponse.ok || !attachmentResponse.ok) {
      throw new Error('The site editing context could not be loaded.')
    }

    resetSiteFormContext()
    storedThing.value = thing
    tags.value = tagResponse.data
    photos.value = attachmentResponse.data
    editingSite.value = site
    showEditSiteForm.value = true
  } catch (error) {
    console.error('Error preparing site editor', error)
    Snackbar.error(`Unable to edit ${site.name}. Please try again.`)
  }
}

const closeSiteEditor = async () => {
  showEditSiteForm.value = false
  editingSite.value = undefined
  resetSiteFormContext()
  await loadThings()
}

const openSiteDeletion = async (site: ThingSiteSummary) => {
  if (!hasSitePermission(site, PermissionAction.Delete)) return

  const thing = await fetchSite(site)
  if (!thing) return

  storedThing.value = thing
  deletingSite.value = thing
  showDeleteSiteDialog.value = true
}

const closeSiteDeletion = () => {
  showDeleteSiteDialog.value = false
  deletingSite.value = undefined
}

const deleteSite = async () => {
  if (!deletingSite.value) return

  const siteId = deletingSite.value.id
  try {
    const response = await hs.things.delete(siteId)
    if (!response.ok) throw new Error(response.message)

    if (selectedThingId.value === siteId) selectedThingId.value = undefined
    closeSiteDeletion()
    await loadThings()
    Snackbar.success('Site deleted.')
  } catch (error) {
    console.error('Error deleting site', error)
    Snackbar.error('Unable to delete the site. Please try again.')
  }
}

const switchToAccessControl = () => {
  showDeleteSiteDialog.value = false
  showAccessControlDialog.value = true
}

const closeAccessControl = async () => {
  showAccessControlDialog.value = false
  deletingSite.value = undefined
  await loadThings()
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
