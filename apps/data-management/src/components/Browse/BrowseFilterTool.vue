<template>
  <v-navigation-drawer v-model="sidebar.isOpen" width="400">
    <v-list>
      <v-list-subheader class="text-h6 mb-2 mt-1">
        Browse data collection sites
      </v-list-subheader>

      <v-divider />

      <v-list-item class="d-flex justify-end mt-2">
        <v-btn
          color="primary-darken-2"
          variant="outlined"
          rounded="xl"
          @click="onClearFilters"
          :append-icon="mdiClose"
          >Clear filters</v-btn
        >
      </v-list-item>

      <v-list-item>
        <v-autocomplete
          class="pt-2"
          v-model="selectedSite"
          :items="availableSites"
          :item-props="
            (site) => ({
              subtitle: site.siteType,
            })
          "
          name="browse-site-search"
          item-title="name"
          return-object
          clearable
          :prepend-inner-icon="mdiMapMarker"
          label="Search sites"
          autocomplete="new-password"
          hide-details
          color="primary"
          no-data-text="No sites found"
        />
      </v-list-item>

      <v-list-item>
        <v-autocomplete
          class="pt-2"
          v-model="selectedWorkspaces"
          :items="availableWorkspaces"
          :item-props="(ws) => ({ subtitle: `Owned by: ${ws?.owner?.name}` })"
          name="browse-workspace-filter"
          item-title="name"
          return-object
          clearable
          :prepend-inner-icon="mdiDomain"
          label="Workspaces"
          autocomplete="new-password"
          multiple
          hide-details
          color="primary"
        >
          <template v-slot:selection="{ item, index }">
            <v-chip
              color="primary-darken-2"
              rounded
              closable
              density="comfortable"
              @click:close="selectedWorkspaces.splice(index, 1)"
            >
              <span>{{ item.title }}</span>
            </v-chip>
          </template>
        </v-autocomplete>
      </v-list-item>

      <v-list-item>
        <v-autocomplete
          class="pt-2"
          label="Site types"
          v-model="selectedSiteTypes"
          :items="availableSiteTypes"
          name="browse-site-type-filter"
          clearable
          :prepend-inner-icon="mdiWaterPump"
          autocomplete="new-password"
          multiple
          hide-details
          color="primary"
        >
          <template v-slot:selection="{ item, index }">
            <v-chip
              color="primary-darken-2"
              rounded
              density="comfortable"
              closable
              @click:close="selectedSiteTypes.splice(index, 1)"
            >
              <span>{{ item.title }}</span>
            </v-chip>
          </template>
        </v-autocomplete>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { useDisplay } from 'vuetify/lib/framework.mjs'
import { useSidebarStore } from '@/store/useSidebar'
import { useVocabularyStore } from '@/composables/useVocabulary'
import { filterThingMarkers } from '@/utils/browseFilters'
import hs, { Workspace } from '@hydroserver/client'
import type { ThingMarker } from '@/types'
import { mdiClose, mdiDomain, mdiMapMarker, mdiWaterPump } from '@mdi/js'

const { smAndDown } = useDisplay()
const vocabularyStore = useVocabularyStore()

const selectedSiteTypes = ref<string[]>([])
const selectedWorkspaces = ref<Workspace[]>([])
const selectedSite = ref<ThingMarker | null>(null)
const workspaces = ref<Workspace[]>([])

const emit = defineEmits(['filter'])
const props = defineProps({
  things: {
    type: Array as () => ThingMarker[],
    required: true,
  },
})

const sidebar = useSidebarStore()
sidebar.isOpen = !!smAndDown

const sortedThings = computed(() =>
  [...props.things].sort((a, b) => a.name.localeCompare(b.name))
)

const availableSites = computed(() =>
  filterThingMarkers(
    sortedThings.value,
    selectedWorkspaces.value,
    selectedSiteTypes.value
  )
)

const availableWorkspaces = computed(() => {
  const workspaceIds = new Set(
    filterThingMarkers(
      props.things,
      [],
      selectedSiteTypes.value,
      selectedSite.value
    ).map((thing) => thing.workspaceId)
  )

  return workspaces.value.filter((workspace) => workspaceIds.has(workspace.id))
})

const availableSiteTypes = computed(() => {
  const siteTypes = new Set(
    filterThingMarkers(
      props.things,
      selectedWorkspaces.value,
      [],
      selectedSite.value
    ).map((thing) => thing.siteType)
  )

  return vocabularyStore.siteTypes.filter((siteType) => siteTypes.has(siteType))
})

const emitFilteredThings = () => {
  const filteredThings = filterThingMarkers(
    props.things,
    selectedWorkspaces.value,
    selectedSiteTypes.value,
    selectedSite.value
  )
  emit('filter', filteredThings)
}

const onClearFilters = () => {
  selectedSiteTypes.value = []
  selectedWorkspaces.value = []
  selectedSite.value = null
}

onMounted(async () => {
  workspaces.value = await hs.workspaces.listAllItems({
    order_by: ['name'],
    expand_related: true,
  })
})

watch([selectedSiteTypes, selectedWorkspaces, selectedSite], emitFilteredThings, {
  deep: true,
})

watch(availableSites, (sites) => {
  if (
    selectedSite.value &&
    !sites.some((site) => site.id === selectedSite.value?.id)
  ) {
    selectedSite.value = null
  }
})

// Drop any selected values that are no longer in the available set when the
// other filters narrow the options.
const pruneSelectionToAvailable = <T, A>(
  selected: Ref<T[]>,
  available: ComputedRef<A[]>,
  selectedKey: (item: T) => unknown,
  availableKey: (item: A) => unknown
) =>
  watch(available, (items) => {
    const availableKeys = new Set(items.map(availableKey))
    const pruned = selected.value.filter((item) =>
      availableKeys.has(selectedKey(item))
    )
    if (pruned.length !== selected.value.length) {
      selected.value = pruned
    }
  })

pruneSelectionToAvailable(
  selectedWorkspaces,
  availableWorkspaces,
  (workspace) => workspace.id,
  (workspace) => workspace.id
)

pruneSelectionToAvailable(
  selectedSiteTypes,
  availableSiteTypes,
  (siteType) => siteType,
  (siteType) => siteType
)
</script>
