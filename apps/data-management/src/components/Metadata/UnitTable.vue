<template>
  <v-data-table-virtual
    :headers="UnitHeaders"
    :items="sortedItems"
    :search="search"
    height="100%"
    fixed-header
  >
    <template v-slot:item.scope="{ item }">
      <MetadataScopeChip :scope="item._scope" />
    </template>
    <template v-slot:item.actions="{ item }">
      <v-icon
        v-if="canEdit && (item._scope !== 'system' || canManageSystem)"
        :icon="mdiPencil"
        color="grey-darken-2"
        :data-testid="`edit-metadata-${item.id}`"
        aria-label="Edit metadata item"
        @click="openDialog(item, 'edit')"
      />
      <v-icon
        v-if="canDelete && (item._scope !== 'system' || canManageSystem)"
        :icon="mdiTrashCanOutline"
        color="grey-darken-2"
        :data-testid="`delete-metadata-${item.id}`"
        aria-label="Delete metadata item"
        @click="openDialog(item, 'delete')"
      />
    </template>
  </v-data-table-virtual>

  <v-dialog v-model="openEdit" width="60rem">
    <UnitFormCard
      :unit="item"
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
      itemName="unit"
      :itemID="item.id"
      parameter-name="unit_id"
      @delete="onDelete"
      @close="openDelete = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import UnitFormCard from '@/components/Metadata/UnitFormCard.vue'
import DeleteMetadataCard from '@/components/Metadata/DeleteMetadataCard.vue'
import MetadataScopeChip from '@/components/Metadata/MetadataScopeChip.vue'
import hs, { Unit } from '@hydroserver/client'
import { useTableLogic } from '@/composables/useTableLogic'
import { computed, toRef } from 'vue'
import { useSystemTableLogic } from '@/composables/useSystemTableLogic'
import { useAllScopeTableLogic } from '@/composables/useAllScopeTableLogic'
import { mdiTrashCanOutline, mdiPencil } from '@mdi/js'

const props = defineProps<{
  search: string | undefined
  workspaceId?: string
  canEdit: boolean
  canDelete: boolean
  canManageSystem?: boolean
  scope?: 'workspace' | 'system' | 'all'
}>()

const { item, items, openEdit, openDelete, openDialog, onUpdate, onDelete } =
  props.scope === 'all'
    ? useAllScopeTableLogic(
        async (wsId: string) =>
          await hs.units.listAllItems({ workspace_id: [wsId] }),
        () => hs.units.listAllItems({ workspace_id: ['null'] }),
        hs.units.delete,
        Unit,
        toRef(props, 'workspaceId')
      )
    : props.workspaceId
      ? useTableLogic(
          async (wsId: string) =>
            await hs.units.listAllItems({ workspace_id: [wsId] }),
          hs.units.delete,
          Unit,
          toRef(props, 'workspaceId')
        )
      : useSystemTableLogic(
          () => hs.units.listAllItems({ workspace_id: ['null'] }),
          (id: string) => hs.units.delete(id),
          Unit
        )

const UnitHeaders = computed(() => {
  const base: {
    title: string
    key: string
    sortable?: boolean
    align?: 'end'
  }[] = [
    { title: 'Name', key: 'name' },
    { title: 'Type', key: 'type' },
    { title: 'Symbol', key: 'symbol' },
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
