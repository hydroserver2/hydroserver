<template>
  <MetadataItemTable
    :items="items"
    :loading="isLoading"
    :search="search"
    kind="processingLevel"
    :default-scope="workspaceId ? 'workspace' : 'system'"
    :show-scope="scope === 'all'"
  >
    <template #actions="{ item }">
      <PermissionTooltip
        :has-permission="
          canEdit && (item._scope !== 'system' || canManageSystem)
        "
        message="You don't have permission to edit this metadata item."
      >
        <template #default>
          <v-btn-icon
            :icon="mdiPencil"
            class="hs-table-icon-action"
            size="small"
            :data-testid="`edit-metadata-${item.id}`"
            aria-label="Edit metadata item"
            @click="openDialog(item, 'edit')"
          />
        </template>
        <template #denied>
          <v-btn-icon
            :icon="mdiPencilOffOutline"
            class="hs-table-icon-action"
            size="small"
            disabled
            aria-label="Edit metadata item unavailable"
          />
        </template>
      </PermissionTooltip>
      <PermissionTooltip
        :has-permission="
          canDelete && (item._scope !== 'system' || canManageSystem)
        "
        message="You don't have permission to delete this metadata item."
      >
        <template #default>
          <v-btn-icon
            :icon="mdiTrashCanOutline"
            class="hs-table-icon-action hs-table-icon-action--danger"
            size="small"
            :data-testid="`delete-metadata-${item.id}`"
            aria-label="Delete metadata item"
            @click="openDialog(item, 'delete')"
          />
        </template>
        <template #denied>
          <v-btn-icon
            :icon="mdiDeleteOffOutline"
            class="hs-table-icon-action hs-table-icon-action--danger"
            size="small"
            disabled
            aria-label="Delete metadata item unavailable"
          />
        </template>
      </PermissionTooltip>
    </template>
  </MetadataItemTable>

  <v-dialog v-model="openEdit" width="60rem">
    <ProcessingLevelFormCard
      :processing-level="item"
      @close="openEdit = false"
      @updated="onUpdate"
      v-bind="{
        ...(workspaceId && item._scope !== 'system'
          ? { 'workspace-id': workspaceId }
          : {}),
      }"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DeleteMetadataCard
      itemName="processing level"
      :itemID="item.id"
      parameter-name="processing_level_id"
      @delete="onDelete"
      @close="openDelete = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import ProcessingLevelFormCard from '@/components/Metadata/ProcessingLevelFormCard.vue'
import DeleteMetadataCard from '@/components/Metadata/DeleteMetadataCard.vue'
import MetadataItemTable from '@/components/Metadata/MetadataItemTable.vue'
import hs, { ProcessingLevel } from '@hydroserver/client'
import { toRef } from 'vue'
import { useSystemTableLogic } from '@/composables/useSystemTableLogic'
import { useAllScopeTableLogic } from '@/composables/useAllScopeTableLogic'
import {
  mdiDeleteOffOutline,
  mdiPencil,
  mdiPencilOffOutline,
  mdiTrashCanOutline,
} from '@mdi/js'
import PermissionTooltip from '@/components/PermissionTooltip.vue'

const props = defineProps<{
  search: string | undefined
  workspaceId?: string
  canEdit: boolean
  canDelete: boolean
  canManageSystem?: boolean
  scope?: 'workspace' | 'system' | 'all'
}>()

const {
  item,
  items,
  isLoading,
  openEdit,
  openDelete,
  openDialog,
  onUpdate,
  onDelete,
} =
  props.workspaceId
    ? useAllScopeTableLogic(
        async (wsId: string) =>
          await hs.processingLevels.listAllItems({ workspace_id: [wsId] }),
        () => hs.processingLevels.listAllItems({ workspace_id: ['null'] }),
        hs.processingLevels.delete,
        ProcessingLevel,
        toRef(props, 'workspaceId'),
        toRef(() => props.scope ?? 'workspace')
      )
    : useSystemTableLogic(
        () => hs.processingLevels.listAllItems({ workspace_id: ['null'] }),
        (id: string) => hs.processingLevels.delete(id),
        ProcessingLevel
      )
</script>
