<template>
  <v-data-table-virtual
    :headers="headers"
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
    <ObservedPropertyFormCard
      :observedProperty="item"
      @close="openEdit = false"
      @updated="onUpdate"
      v-bind="{
        ...(workspaceId ? { 'workspace-id': workspaceId } : {}),
      }"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DeleteMetadataCard
      itemName="observedProperty"
      :itemID="item.id"
      parameter-name="observed_property_id"
      @delete="onDelete"
      @close="openDelete = false"
      v-bind="{
        ...(workspaceId ? { 'workspace-id': workspaceId } : {}),
      }"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import ObservedPropertyFormCard from '@/components/Metadata/ObservedPropertyFormCard.vue'
import DeleteMetadataCard from '@/components/Metadata/DeleteMetadataCard.vue'
import hs, { ObservedProperty } from '@hydroserver/client'
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
          await hs.observedProperties.listAllItems({ workspace_id: [wsId] }),
        hs.observedProperties.delete,
        ObservedProperty,
        toRef(props, 'workspaceId')
      )
    : useSystemTableLogic(
        () => hs.observedProperties.listAllItems(),
        (id: string) => hs.observedProperties.delete(id),
        ObservedProperty
      )

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Type', key: 'type' },
  { title: 'Code', key: 'code' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
] as const

const sortedItems = computed(() =>
  items.value.sort((a, b) => a.name.localeCompare(b.name))
)
</script>
