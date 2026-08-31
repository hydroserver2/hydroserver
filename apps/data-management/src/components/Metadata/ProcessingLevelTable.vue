<template>
  <v-skeleton-loader
    v-if="isLoading"
    type="table"
    class="metadata-table-loading-skeleton"
  />
  <v-data-table-virtual
    v-else
    :headers="ProcLevelHeaders"
    :items="sortedItems"
    :search="search"
    fixed-header
  >
    <template v-slot:item.scope="{ item }">
      <MetadataScopeChip :scope="item._scope" />
    </template>
    <template v-slot:item.actions="{ item }">
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
  </v-data-table-virtual>

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
import MetadataScopeChip from '@/components/Metadata/MetadataScopeChip.vue'
import hs, { ProcessingLevel } from '@hydroserver/client'
import { useTableLogic } from '@/composables/useTableLogic'
import { computed, toRef } from 'vue'
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
  props.scope === 'all'
    ? useAllScopeTableLogic(
        async (wsId: string) =>
          await hs.processingLevels.listAllItems({ workspace_id: [wsId] }),
        () => hs.processingLevels.listAllItems({ workspace_id: ['null'] }),
        hs.processingLevels.delete,
        ProcessingLevel,
        toRef(props, 'workspaceId')
      )
    : props.workspaceId
      ? useTableLogic(
          async (wsId: string) =>
            await hs.processingLevels.listAllItems({ workspace_id: [wsId] }),
          hs.processingLevels.delete,
          ProcessingLevel,
          toRef(props, 'workspaceId')
        )
      : useSystemTableLogic(
          () => hs.processingLevels.listAllItems({ workspace_id: ['null'] }),
          (id: string) => hs.processingLevels.delete(id),
          ProcessingLevel
        )

const ProcLevelHeaders = computed(() => {
  const base: {
    title: string
    key: string
    sortable?: boolean
    align?: 'end'
  }[] = [
    { title: 'Name', key: 'name' },
    { title: 'Code', key: 'code' },
    { title: 'Description', key: 'description' },
    { title: 'Definition', key: 'definition' },
  ]
  if (props.scope === 'all')
    base.push({ title: 'Scope', key: 'scope', sortable: false })
  base.push({ title: 'Actions', key: 'actions', sortable: false, align: 'end' })
  return base
})

const sortedItems = computed(() =>
  items.value.sort((a, b) => a.name.localeCompare(b.name))
)
</script>
