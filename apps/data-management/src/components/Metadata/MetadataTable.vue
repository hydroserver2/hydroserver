<template>
  <div
    v-if="activeWorkspace"
    class="metadata-section"
    :data-testid="`${scope}-metadata-table`"
  >
    <div class="metadata-header">
      <h6 class="text-h6">Metadata</h6>
      <v-icon
        :icon="mdiHelpCircleOutline"
        @click="showHelp = !showHelp"
        color="grey"
        size="18"
        class="metadata-help-icon"
      />
    </div>

    <p v-if="showHelp" class="metadata-help-text">
      Methods, units, and other reference metadata used by this workspace's
      datastreams. Workspace items are yours to edit; system items are shared
      platform defaults managed by administrators.
    </p>

    <v-btn-toggle
      v-model="scope"
      mandatory
      density="compact"
      color="primary"
      variant="outlined"
      rounded="xl"
      divided
      class="mb-2"
    >
      <v-btn value="all">All</v-btn>
      <v-btn value="workspace">Workspace metadata</v-btn>
      <v-btn value="system">System metadata</v-btn>
    </v-btn-toggle>

    <v-tabs
      v-model="tab"
      color="primary"
      density="compact"
      class="metadata-type-tabs"
      show-arrows
    >
      <v-tab v-for="item in metaMap" :key="item.name">{{ item.name }}</v-tab>
    </v-tabs>

    <v-card class="hs-table-card metadata-table-card" flat>
      <v-toolbar flat density="compact">
        <v-text-field
          class="mx-4 metadata-search"
          clearable
          v-model="search"
          :prepend-inner-icon="mdiMagnify"
          label="Search metadata"
          hide-details
          variant="underlined"
          density="compact"
          rounded="xl"
        />

        <v-spacer />

        <v-btn-add
          v-if="canCreateMetadata"
          class="mr-2"
          :prependIcon="mdiPlus"
          :data-testid="`add-${scope}-metadata-item`"
          @click="metaMap[tab]?.openDialog()"
          >Add new {{ metaMap[tab]?.singularName }}</v-btn-add
        >
      </v-toolbar>

      <v-window v-model="tab" class="metadata-window">
        <v-window-item :value="0">
          <MethodTable
            :key="`${scope}-${methodKey}`"
            :search="search"
            :workspace-id="workspaceId"
            :can-edit="canEditMetadata"
            :can-delete="canDeleteMetadata"
            :scope="scope"
          />
        </v-window-item>

        <v-window-item :value="1">
          <ObservedPropertyTable
            :key="`${scope}-${OPKey}`"
            :search="search"
            :workspace-id="workspaceId"
            :can-edit="canEditMetadata"
            :can-delete="canDeleteMetadata"
            :scope="scope"
          />
        </v-window-item>

        <v-window-item :value="2">
          <ProcessingLevelTable
            :key="`${scope}-${PLKey}`"
            :search="search"
            :workspace-id="workspaceId"
            :can-edit="canEditMetadata"
            :can-delete="canDeleteMetadata"
            :scope="scope"
          />
        </v-window-item>

        <v-window-item :value="3">
          <UnitTable
            :key="`${scope}-${unitKey}`"
            :search="search"
            :workspace-id="workspaceId"
            :can-edit="canEditMetadata"
            :can-delete="canDeleteMetadata"
            :scope="scope"
          />
        </v-window-item>

        <v-window-item :value="4">
          <ResultQualifierTable
            :key="`${scope}-${qualifierKey}`"
            :search="search"
            :workspace-id="workspaceId"
            :can-edit="canEditMetadata"
            :can-delete="canDeleteMetadata"
            :scope="scope"
          />
        </v-window-item>
      </v-window>
    </v-card>
  </div>

  <v-dialog v-model="openMethodCreate" width="60rem">
    <MethodFormCard
      @close="openMethodCreate = false"
      @created="refreshMethodTable"
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
import MethodTable from '@/components/Metadata/MethodTable.vue'
import ResultQualifierTable from '@/components/Metadata/ResultQualifierTable.vue'
import ProcessingLevelTable from '@/components/Metadata/ProcessingLevelTable.vue'
import ObservedPropertyTable from '@/components/Metadata/ObservedPropertyTable.vue'
import UnitFormCard from '@/components/Metadata/UnitFormCard.vue'
import MethodFormCard from '@/components/Metadata/MethodFormCard.vue'
import ResultQualifierFormCard from '@/components/Metadata/ResultQualifierFormCard.vue'
import ProcessingLevelFormCard from '@/components/Metadata/ProcessingLevelFormCard.vue'
import ObservedPropertyFormCard from '@/components/Metadata/ObservedPropertyFormCard.vue'
import { computed, ref } from 'vue'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'
import {
  PermissionAction,
  PermissionResource,
  Workspace,
} from '@hydroserver/client'
import { useMetadata } from '@/store/metadata'
import { mdiHelpCircleOutline, mdiMagnify, mdiPlus } from '@mdi/js'

type MetadataScope = 'workspace' | 'system' | 'all'

// The active metadata type (Methods/Observed properties/...) lives in a
// store rather than local state so it survives this component remounting
// when the selected workspace changes.
const { tab } = storeToRefs(useMetadata())
const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

const props = defineProps({
  /** Workspace to show metadata for. Falls back to the globally selected workspace. */
  workspace: Object as () => Workspace,
})

const scope = ref<MetadataScope>('workspace')
const search = ref('')
const showHelp = ref(false)

const activeWorkspace = computed<Workspace | undefined>(
  () => props.workspace ?? selectedWorkspace.value ?? undefined
)

// System-only tables don't need a workspace, but workspace and merged ("all")
// tables both fetch this workspace's items alongside/instead of system ones.
const workspaceId = computed(() =>
  scope.value === 'system' ? undefined : activeWorkspace.value!.id
)

const { hasPermission, isAdmin } = useWorkspacePermissions(activeWorkspace)

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

const openMethodCreate = ref(false)
const methodKey = ref(0)
const refreshMethodTable = () => (methodKey.value += 1)

const metaMap: Record<string, any> = {
  0: {
    name: 'Methods',
    openDialog: () => (openMethodCreate.value = true),
    singularName: 'method',
    resource: PermissionResource.Method,
  },
  1: {
    name: 'Observed properties',
    openDialog: () => (openOPCreate.value = true),
    singularName: 'observed property',
    resource: PermissionResource.ObservedProperty,
  },
  2: {
    name: 'Processing levels',
    openDialog: () => (openPLCreate.value = true),
    singularName: 'processing level',
    resource: PermissionResource.ProcessingLevel,
  },
  3: {
    name: 'Units',
    openDialog: () => (openUnitCreate.value = true),
    singularName: 'unit',
    resource: PermissionResource.Unit,
  },
  4: {
    name: 'Result qualifiers',
    openDialog: () => (openRQCreate.value = true),
    singularName: 'result qualifier',
    resource: PermissionResource.ResultQualifier,
  },
}

const hasMetadataPermission = (action: PermissionAction) => {
  if (scope.value === 'system') return isAdmin()
  const resource = metaMap[tab.value]?.resource as
    PermissionResource | undefined
  return !!(
    resource &&
    activeWorkspace.value &&
    hasPermission(resource, action, activeWorkspace.value)
  )
}

const canCreateMetadata = computed(() =>
  hasMetadataPermission(PermissionAction.Create)
)
const canEditMetadata = computed(() =>
  hasMetadataPermission(PermissionAction.Edit)
)
const canDeleteMetadata = computed(() =>
  hasMetadataPermission(PermissionAction.Delete)
)
</script>

<style scoped>
.metadata-header {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 2px;
}
.metadata-help-icon {
  cursor: pointer;
}
.metadata-help-text {
  font-size: 12.5px;
  color: #6b7280;
  line-height: 1.5;
  max-width: 640px;
  margin-bottom: 10px;
}
.metadata-type-tabs {
  margin: 0 0 2px;
}
.metadata-table-card {
  margin-top: 6px;
}
.metadata-search {
  max-width: 260px;
  flex-shrink: 0;
}
.metadata-window :deep(td),
.metadata-window :deep(th) {
  font-size: 13px;
}
</style>
