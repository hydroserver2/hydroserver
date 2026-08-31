<template>
  <div
    v-if="activeWorkspace"
    class="metadata-section"
    :data-testid="`${scope}-metadata-table`"
  >
    <div class="hs-table-tools">
      <HsSearchInput v-model="search" placeholder="Search metadata…" />

      <v-btn-icon
        :icon="mdiHelpCircleOutline"
        size="small"
        title="About metadata"
        aria-label="Toggle metadata help"
        :aria-expanded="showHelp"
        @click="showHelp = !showHelp"
      />

      <div class="hs-table-actions">
        <v-btn-page-action
          v-if="canCreateMetadata"
          :data-testid="`add-${scope}-metadata-item`"
          @click="metaMap[tab]?.openDialog()"
          >Add new {{ metaMap[tab]?.singularName }}</v-btn-page-action
        >
      </div>
    </div>

    <p v-if="showHelp" class="metadata-help-text">
      <small>
        Methods, units, and other reference metadata used by this workspace's
        datastreams. Workspace items are yours to edit; system items are shared
        platform defaults managed by administrators.
      </small>
    </p>

    <div class="hs-table-card metadata-table-frame">
      <div class="metadata-table-selector">
        <v-tabs
          v-model="tab"
          color="primary"
          density="compact"
          class="metadata-type-tabs"
          show-arrows
        >
          <v-tab v-for="item in metaMap" :key="item.name">
            {{ item.name }}
          </v-tab>
        </v-tabs>

        <v-chip-group
          v-model="scope"
          variant="plain"
          mandatory
          selected-class="bg-primary-lighten-2"
        >
          <v-chip
            value="all"
            data-testid="metadata-scope-all"
            class="metadata-scope-chip hs-text-sm"
            size="small"
            label
          >
            All
          </v-chip>
          <v-chip
            value="workspace"
            data-testid="metadata-scope-workspace"
            class="metadata-scope-chip hs-text-sm"
            size="small"
            label
          >
            Workspace
          </v-chip>
          <v-chip
            value="system"
            data-testid="metadata-scope-system"
            class="metadata-scope-chip hs-text-sm"
            size="small"
            label
          >
            System
          </v-chip>
        </v-chip-group>
      </div>

      <v-card class="metadata-table-card" flat>
        <v-window v-model="tab" class="metadata-window">
          <v-window-item :value="0">
            <MethodTable
              :key="`${scope}-${methodKey}`"
              :search="search"
              :workspace-id="workspaceId"
              :can-edit="canEditMetadata"
              :can-delete="canDeleteMetadata"
              :can-manage-system="canManageSystemMetadata"
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
              :can-manage-system="canManageSystemMetadata"
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
              :can-manage-system="canManageSystemMetadata"
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
              :can-manage-system="canManageSystemMetadata"
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
              :can-manage-system="canManageSystemMetadata"
              :scope="scope"
            />
          </v-window-item>
        </v-window>
      </v-card>
    </div>
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
import { HsSearchInput } from '@hydroserver/design-system/vue'
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
import { mdiHelpCircleOutline } from '@mdi/js'

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

const scope = ref<MetadataScope>('all')
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
    | PermissionResource
    | undefined
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
const canManageSystemMetadata = computed(() => isAdmin())
</script>

<style scoped>
.metadata-section {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
.metadata-help-text {
  color: var(--hs-text-secondary);
  line-height: 1.5;
  max-width: 640px;
  margin-bottom: var(--hs-space-10);
}
.metadata-type-tabs {
  flex: 1;
  min-width: 0;
}
.metadata-table-frame {
  display: flex;
  flex: 0 1 auto;
  flex-direction: column;
  min-height: 0;
}
.metadata-table-selector {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  min-height: 42px;
  background: var(--hs-surface-subtle);
  border-bottom: 1px solid var(--hs-border);
}
.metadata-scope-toggle {
  flex-shrink: 0;
  margin: var(--hs-space-4) var(--hs-space-8) var(--hs-space-4)
    var(--hs-space-12);
  gap: var(--hs-space-4);
}
.metadata-scope-chip {
  border-radius: var(--hs-radius-sm);
  padding-inline: var(--hs-space-6);
  min-height: var(--hs-space-24);
}
.metadata-table-card {
  display: flex;
  flex: 0 1 auto;
  flex-direction: column;
  min-height: 0;
  margin-top: 0;
  border-radius: 0;
  overflow: hidden;
}
.metadata-window {
  flex: 0 1 auto;
  min-height: 0;
}
.metadata-window :deep(.v-window__container),
.metadata-window :deep(.v-window-item) {
  height: 100%;
  min-height: 0;
}
.metadata-window :deep(.v-data-table) {
  height: auto;
  max-height: 100%;
  min-height: 0;
  overflow: hidden;
}
.metadata-window :deep(.v-data-table .v-table__wrapper) {
  max-height: 100%;
  overflow-y: auto;
}
.metadata-window :deep(.metadata-table-loading-skeleton) {
  min-height: 360px;
  height: 100%;
  background: var(--hs-surface);
}
.metadata-window
  :deep(.v-table--fixed-header > .v-table__wrapper > table > thead) {
  position: sticky;
  top: 0;
  z-index: 2;
}
.metadata-window
  :deep(.v-table--fixed-header > .v-table__wrapper > table > thead > tr > th) {
  background: var(--hs-surface-muted);
}
.metadata-window :deep(td),
.metadata-window :deep(th) {
  /* No template element reachable inside v-data-table internals. */
  font-size: var(--hs-font-sm);
}

@media (max-width: 900px) {
  .metadata-table-selector {
    align-items: stretch;
    flex-direction: column;
  }

  .metadata-scope-toggle {
    align-self: flex-end;
    margin-top: 0;
  }
}
</style>
