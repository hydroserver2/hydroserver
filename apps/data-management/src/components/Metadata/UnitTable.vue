<template>
  <v-data-table-virtual
    :headers="UnitHeaders"
    :items="sortedItems"
    :search="search"
    :style="{ 'max-height': `400px` }"
    fixed-header
  >
    <template v-slot:item.actions="{ item }" v-if="canEdit">
      <v-icon :icon="mdiPencil" @click="openDialog(item, 'edit')" />
      <v-icon :icon="mdiDelete" @click="openDialog(item, 'delete')" />
    </template>
  </v-data-table-virtual>

  <v-dialog v-model="openEdit" width="60rem">
    <UnitFormCard
      :unit="item"
      @close="openEdit = false"
      @updated="onUpdate"
      v-bind="{
        ...(workspaceId ? { 'workspace-id': workspaceId } : {}),
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
import hs, { Unit } from '@hydroserver/client'
import { useTableLogic } from '@/composables/useTableLogic'
import { computed, toRef } from 'vue'
import { useSystemTableLogic } from '@/composables/useSystemTableLogic'
import { mdiDelete, mdiPencil } from '@mdi/js'

const props = defineProps<{
  search: string | undefined
  workspaceId?: string
  canEdit: Boolean
}>()

const { item, items, openEdit, openDelete, openDialog, onUpdate, onDelete } =
  props.workspaceId
    ? useTableLogic(
        async (wsId: string) =>
          await hs.units.listAllItems({ workspace_id: [wsId] }),
        hs.units.delete,
        Unit,
        toRef(props, 'workspaceId')
      )
    : useSystemTableLogic(
        () => hs.units.listAllItems(),
        (id: string) => hs.units.delete(id),
        Unit
      )

const UnitHeaders = [
  { title: 'Name', key: 'name' },
  { title: 'Type', key: 'type' },
  { title: 'Symbol', key: 'symbol' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
] as const

const sortedItems = computed(() =>
  items.value.sort((a, b) => a.name.localeCompare(b.name))
)
</script>
