<template>
  <div
    v-if="activeWorkspace"
    class="metadata-section"
    :data-testid="`${scope}-metadata-table`"
  >
    <div class="metadata-section-header">
      <div>
        <h3 class="metadata-section-title">{{ sectionTitle }}</h3>
        <p class="metadata-section-subtitle">{{ sectionSubtitle }}</p>
      </div>

      <v-btn-add
        v-if="hasCRUDPermissions"
        :prependIcon="mdiPlus"
        :data-testid="`add-${scope}-metadata-item`"
        @click="metaMap[tab]?.openDialog()"
        >Add new {{ metaMap[tab]?.singularName }}</v-btn-add
      >
    </div>

    <v-tabs
      v-model="tab"
      color="primary"
      density="comfortable"
      class="metadata-type-tabs"
      show-arrows
    >
      <v-tab v-for="item in metaMap" :key="item.name">{{ item.name }}</v-tab>
    </v-tabs>

    <v-window v-model="tab" class="metadata-window">
      <v-window-item :value="0">
        <SensorTable
          :key="sensorKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
          :scope="scope"
        />
      </v-window-item>

      <v-window-item :value="1">
        <ObservedPropertyTable
          :key="OPKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
          :scope="scope"
        />
      </v-window-item>

      <v-window-item :value="2">
        <ProcessingLevelTable
          :key="PLKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
          :scope="scope"
        />
      </v-window-item>

      <v-window-item :value="3">
        <UnitTable
          :key="unitKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
          :scope="scope"
        />
      </v-window-item>

      <v-window-item :value="4">
        <ResultQualifierTable
          :key="qualifierKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
          :scope="scope"
        />
      </v-window-item>
    </v-window>
  </div>

  <v-dialog v-model="openSensorCreate" width="60rem">
    <SensorFormCard
      @close="openSensorCreate = false"
      @created="refreshSensorTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>

  <v-dialog v-model="openOPCreate" width="60rem">
    <ObservedPropertyFormCard
      @close="openOPCreate = false"
      @created="refreshOPTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>

  <v-dialog v-model="openPLCreate" width="60rem">
    <ProcessingLevelFormCard
      @close="openPLCreate = false"
      @created="refreshPLTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>

  <v-dialog v-model="openUnitCreate" width="60rem">
    <UnitFormCard
      @close="openUnitCreate = false"
      @created="refreshUnitTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>

  <v-dialog v-model="openRQCreate" width="60rem">
    <ResultQualifierFormCard
      @close="openRQCreate = false"
      @created="refreshRQTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>
</template>

<script lang="ts" setup>
import UnitTable from '@/components/Metadata/UnitTable.vue'
import SensorTable from '@/components/Metadata/SensorTable.vue'
import ResultQualifierTable from '@/components/Metadata/ResultQualifierTable.vue'
import ProcessingLevelTable from '@/components/Metadata/ProcessingLevelTable.vue'
import ObservedPropertyTable from '@/components/Metadata/ObservedPropertyTable.vue'
import UnitFormCard from '@/components/Metadata/UnitFormCard.vue'
import SensorFormCard from '@/components/Metadata/SensorFormCard.vue'
import ResultQualifierFormCard from '@/components/Metadata/ResultQualifierFormCard.vue'
import ProcessingLevelFormCard from '@/components/Metadata/ProcessingLevelFormCard.vue'
import ObservedPropertyFormCard from '@/components/Metadata/ObservedPropertyFormCard.vue'
import { computed, ref, type PropType } from 'vue'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'
import { Workspace } from '@hydroserver/client'
import { useMetadata } from '@/store/metadata'
import { mdiPlus } from '@mdi/js'

export type MetadataScope = 'workspace' | 'system' | 'all'

// The active metadata type (Methods/Observed properties/...) is shared
// across both the workspace and system sections via this store, so
// switching type in one keeps the other in sync.
const { tab } = storeToRefs(useMetadata())
const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

const props = defineProps({
  scope: {
    type: String as PropType<MetadataScope>,
    default: 'workspace',
  },
  search: String,
  /** Workspace to show metadata for. Falls back to the globally selected workspace. */
  workspace: Object as () => Workspace,
})

const activeWorkspace = computed<Workspace | undefined>(
  () => props.workspace ?? selectedWorkspace.value ?? undefined
)

// System-only tables don't need a workspace, but workspace and merged ("all")
// tables both fetch this workspace's items alongside/instead of system ones.
const workspaceId = computed(() =>
  props.scope === 'system' ? undefined : activeWorkspace.value!.id
)

const { isAdmin } = useWorkspacePermissions(activeWorkspace)

const hasCRUDPermissions = computed(
  () => !!(props.scope !== 'system' || isAdmin())
)

const sectionTitle = computed(
  () =>
    ({ all: 'All metadata', workspace: 'Workspace metadata', system: 'System metadata' })[
      props.scope
    ]
)
const sectionSubtitle = computed(
  () =>
    ({
      all: "This workspace's own metadata alongside the system-wide defaults available to it.",
      workspace: 'Belongs only to this workspace. Editors and the owner can manage it.',
      system: 'Shared across every workspace and managed by administrators.',
    })[props.scope]
)
const openUnitCreate = ref(false)
const unitKey = ref(0)
const refreshUnitTable = () => (unitKey.value += 1)

const openRQCreate = ref(false)
const qualifierKey = ref(0)
const refreshRQTable = () => (qualifierKey.value += 1)

const openPLCreate = ref(false)
const PLKey = ref(0)
const refreshPLTable = () => (PLKey.value += 1)

const openOPCreate = ref(false)
const OPKey = ref(0)
const refreshOPTable = () => (OPKey.value += 1)

const openSensorCreate = ref(false)
const sensorKey = ref(0)
const refreshSensorTable = () => (sensorKey.value += 1)

const metaMap: Record<string, any> = {
  0: {
    name: 'Methods',
    openDialog: () => (openSensorCreate.value = true),
    singularName: 'method',
  },
  1: {
    name: 'Observed properties',
    openDialog: () => (openOPCreate.value = true),
    singularName: 'observed property',
  },
  2: {
    name: 'Processing levels',
    openDialog: () => (openPLCreate.value = true),
    singularName: 'processing level',
  },
  3: {
    name: 'Units',
    openDialog: () => (openUnitCreate.value = true),
    singularName: 'unit',
  },
  4: {
    name: 'Result qualifiers',
    openDialog: () => (openRQCreate.value = true),
    singularName: 'result qualifier',
  },
}
</script>

<style scoped>
.metadata-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.metadata-section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1c1b1f;
}
.metadata-section-subtitle {
  font-size: 12.5px;
  color: #6b7280;
  margin-top: 2px;
  max-width: 520px;
}
.metadata-type-tabs {
  border-bottom: 1px solid #e8e8e8;
  margin: 12px 0 4px;
}
.metadata-window :deep(td),
.metadata-window :deep(th) {
  font-size: 13px;
}
</style>
