<template>
  <div
    v-if="activeWorkspace"
    class="metadata-section"
    :data-testid="`${scope}-metadata-table`"
  >
    <div class="hs-table-tools">
      <v-text-field
        v-model="search"
        class="hs-table-search"
        clearable
        :prepend-inner-icon="mdiMagnify"
        placeholder="Search metadata"
        aria-label="Search metadata"
        hide-details
        density="compact"
      />

      <div class="hs-table-actions">
        <v-btn
          :icon="mdiHelpCircleOutline"
          variant="text"
          size="small"
          color="grey-darken-2"
          title="About metadata"
          aria-label="Toggle metadata help"
          :aria-expanded="showHelp"
          @click="showHelp = !showHelp"
        />

        <v-btn-primary
          v-if="canCreateMetadata"
          variant="flat"
          :data-testid="`add-${scope}-metadata-item`"
          @click="metaMap[tab]?.openDialog()"
          >Add new {{ metaMap[tab]?.singularName }}</v-btn-primary
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
          mandatory
          selected-class="bg-primary text-white"
          class="metadata-scope-toggle"
        >
          <v-chip
            value="all"
            class="metadata-scope-chip hs-text-sm"
            size="small"
            label
          >
            All
          </v-chip>
          <v-chip
            value="workspace"
            class="metadata-scope-chip hs-text-sm"
            size="small"
            label
          >
            Workspace
          </v-chip>
          <v-chip
            value="system"
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
import { mdiHelpCircleOutline, mdiMagnify } from '@mdi/js'

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
  margin-bottom: 10px;
}
.metadata-type-tabs {
  flex: 1;
  min-width: 0;
}
.metadata-table-frame {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}
.metadata-table-selector {
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
  gap: 4px;
}
.metadata-scope-chip {
  border-radius: 4px;
  padding-inline: 6px;
  min-height: 24px;
}
.metadata-table-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  margin-top: 0;
  border-radius: 0;
  overflow: hidden;
}
.metadata-window {
  flex: 1;
  min-height: 0;
}
.metadata-window :deep(.v-window__container),
.metadata-window :deep(.v-window-item) {
  height: 100%;
  min-height: 0;
}
.metadata-window :deep(.v-data-table) {
  height: 100%;
  max-height: 100%;
  min-height: 0;
  overflow: hidden;
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
