<template>
  <template v-if="isPageLoaded">
    <div class="map-container flex-shrink-0">
      <OpenLayersMap
        v-if="workspaceThings"
        :colorKey="useColors ? filterCriteria.key : ''"
        :things="filteredThings"
      />
    </div>

    <div class="my-4 mx-6">
      <WorkspaceToolbar />

      <v-row class="my-2" v-if="hasWorkspaces && selectedWorkspace !== null">
        <v-col cols="auto">
          <h5 class="text-h5">Your registered sites</h5>
        </v-col>
      </v-row>

      <v-card class="mb-1" elevation="2">
        <KeepAlive>
          <v-expand-transition>
            <SiteFilterToolbar
              v-if="showFilter"
              :useColors="useColors"
              @update:useColors="updateColors"
              @filter="handleFilter"
            />
          </v-expand-transition>
        </KeepAlive>
      </v-card>

      <v-card v-if="hasWorkspaces && selectedWorkspace !== null">
        <v-toolbar flat color="blue-darken-2">
          <v-text-field
            :disabled="!workspaceThings?.length"
            class="mx-4"
            clearable
            v-model="search"
            :prepend-inner-icon="mdiMagnify"
            label="Search"
            hide-details
            variant="underlined"
            density="compact"
            rounded="xl"
          />

          <v-spacer />

          <v-btn
            :disabled="!workspaceThings?.length"
            class="mr-2"
            @click="showFilter = !showFilter"
            :append-icon="showFilter ? mdiMenuUp : mdiMenuDown"
            variant="outlined"
            rounded="xl"
            >Filter sites</v-btn
          >

          <v-btn-add class="mr-2" @click="onClickRegisterSite" color="white">
            Register a new site
          </v-btn-add>
        </v-toolbar>
        <v-data-table-virtual
          :headers="headers"
          :items="coloredThings"
          :sort-by="[{ key: 'samplingFeatureCode' }]"
          :search="search"
          multi-sort
          item-value="id"
          class="elevation-3 owned-sites-table"
          @click:row="onRowClick"
          color="primary"
          :hover="coloredThings?.length > 0 && isPageLoaded"
          :style="{ 'max-height': `200vh` }"
          fixed-header
          :loading="!isPageLoaded"
          loading-text="Loading sites..."
        >
          <template v-slot:no-data>
            <div class="text-center pa-4" v-if="workspaceThings.length === 0">
              <v-icon size="48" color="grey lighten-1" :icon="mdiRadioTower" />
              <h4 class="mt-2">You have not registered any sites</h4>
              <p class="mb-4">
                Click the "Register a new site" button to start managing your
                data.
              </p>
            </div>

            <!-- Check if filters result in no matching sites -->
            <div
              class="text-center pa-4"
              v-else-if="
                workspaceThings.length > 0 && coloredThings.length === 0
              "
            >
              <v-icon
                size="48"
                color="grey lighten-1"
                :icon="mdiFilterRemoveOutline"
              />
              <h4 class="mt-2">No sites match your filters</h4>
              <p class="mb-4">
                Try adjusting your search keywords or filter criteria to find
                sites.
              </p>
            </div>
          </template>
          <template v-slot:item.tagValue="{ item }">
            <template v-for="(tag, index) in item.tags">
              <v-chip
                :color="item.color?.background"
                v-if="tag.key === filterCriteria.key"
              >
                {{ item.tagValue }}
              </v-chip>
            </template>
          </template>
        </v-data-table-virtual>
      </v-card>
    </div>

    <v-dialog v-model="showSiteForm" width="60rem" v-if="selectedWorkspace">
      <SiteForm
        @close="showSiteForm = false"
        :workspace-id="selectedWorkspace.id"
        @site-created="loadThings"
      />
    </v-dialog>
  </template>
  <FullScreenLoader v-else />
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ref, onMounted, computed, watch } from 'vue'
import OpenLayersMap from '@/components/Maps/OpenLayersMap.vue'
import SiteForm from '@/components/Site/SiteForm.vue'
import SiteFilterToolbar from '@/components/Site/SiteFilterToolbar.vue'
import WorkspaceToolbar from '@/components/Workspace/WorkspaceToolbar.vue'
import hs, {
  PermissionResource,
  PermissionAction,
  Thing,
} from '@hydroserver/client'
import { addColorToMarkers } from '@/utils/maps/markers'
import { ThingWithColor } from '@/types'
import { Snackbar } from '@/utils/notifications'
import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import {
  mdiFilterRemoveOutline,
  mdiMagnify,
  mdiMenuDown,
  mdiMenuUp,
  mdiRadioTower,
} from '@mdi/js'

const { selectedWorkspace, hasWorkspaces } = storeToRefs(useWorkspaceStore())
const { setWorkspaces } = useWorkspaceStore()
const { hasPermission } = useWorkspacePermissions()

const workspaceThings = ref<Thing[]>([])
const useColors = ref(true)
const isFiltered = ref(false)
const isPageLoaded = ref(false)
const filterCriteria = ref({ key: '', values: [] as string[] })
const search = ref()

const matchesFilterCriteria = (thing: Thing, key: string, values: string[]) => {
  if (values.length > 0)
    return thing.tags.some(
      (tag) => tag.key === key && values.includes(tag.value)
    )

  return thing.tags.some((tag) => tag.key === key)
}

const matchesSearchCriteria = (thing: Thing) => {
  if (!search.value) return true
  const searchLower = search.value.toLowerCase()
  return (
    thing.samplingFeatureCode?.toLowerCase().includes(searchLower) ||
    thing.name?.toLowerCase().includes(searchLower) ||
    thing.siteType?.toLowerCase().includes(searchLower)
  )
}

const onClickRegisterSite = () => {
  if (hasPermission(PermissionResource.Thing, PermissionAction.Create))
    showSiteForm.value = true
  else
    Snackbar.error(
      "You don't have permissions to register a site for this workspace."
    )
}

watch(selectedWorkspace, async (ws) => {
  await loadThings()
})

const filteredThings = computed(() => {
  const { key, values } = filterCriteria.value
  const hasKey = !!key

  isFiltered.value = hasKey

  return workspaceThings.value.filter((thing) => {
    return (
      matchesSearchCriteria(thing) &&
      (!hasKey || matchesFilterCriteria(thing, key, values))
    )
  })
})

const coloredThings = computed<ThingWithColor[]>(() =>
  addColorToMarkers(filteredThings.value, filterCriteria.value.key)
)

const showSiteForm = ref(false)
const showFilter = ref(false)
const router = useRouter()

const headers = computed(() => {
  const baseHeaders = [
    { title: 'Site code', key: 'samplingFeatureCode' },
    { title: 'Site name', key: 'name' },
    { title: 'Site type', key: 'siteType' },
  ]

  if (isFiltered.value && useColors.value) {
    baseHeaders.push({ title: 'Additional metadata', key: 'tagValue' })
  }

  return baseHeaders
})

const updateColors = (newColor: boolean) => {
  useColors.value = newColor
}

const handleFilter = (criteria: { key: string; values: string[] }) => {
  filterCriteria.value = criteria
}

const onRowClick = (event: Event, item: any) => {
  router.push({ name: 'SiteDetails', params: { id: item.item.id } })
}

const loadThings = async () => {
  workspaceThings.value = await hs.things.listAllItems({
    workspace_id: [selectedWorkspace.value!.id],
  })
}

onMounted(async () => {
  if (selectedWorkspace.value == null) {
    const [workspaceRes] = await Promise.all([
      hs.workspaces.listAllItems({ is_associated: true, expand_related: true }),
    ])
    setWorkspaces(workspaceRes)
  } else {
    const [things, workspaceRes] = await Promise.all([
      hs.things.listAllItems({ workspace_id: [selectedWorkspace.value.id] }),
      hs.workspaces.listAllItems({ is_associated: true, expand_related: true }),
    ])
    setWorkspaces(workspaceRes)
    workspaceThings.value = things
  }
  isPageLoaded.value = true
})
</script>

<style scoped>
.map-container {
  /* The legend won't appear without a relative position */
  position: relative;
  height: 33rem;
}
</style>
