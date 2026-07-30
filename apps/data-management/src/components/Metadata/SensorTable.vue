<template>
  <v-data-table-virtual
    class="hs-table-card"
    :headers="headers"
    :items="sortedItems"
    :search="search"
    :style="{ 'max-height': `400px` }"
    fixed-header
  >
    <template v-slot:item.scope="{ item }">
      <MetadataScopeChip :scope="item._scope" />
    </template>
    <template v-slot:item.actions="{ item }" v-if="canEdit && item._scope !== 'system'">
      <v-icon :icon="mdiPencil" @click="openDialog(item, 'edit')" />
      <v-icon :icon="mdiTrashCanOutline" @click="openDialog(item, 'delete')" />
    </template>
  </v-data-table-virtual>

  <v-dialog v-model="openEdit" width="60rem">
    <SensorFormCard
      :sensor="item"
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
      itemName="method"
      :itemID="item.id"
      parameter-name="sensor_id"
      @delete="onDelete"
      @close="openDelete = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import SensorFormCard from '@/components/Metadata/SensorFormCard.vue'
import DeleteMetadataCard from '@/components/Metadata/DeleteMetadataCard.vue'
import MetadataScopeChip from '@/components/Metadata/MetadataScopeChip.vue'
import hs, { Sensor } from '@hydroserver/client'
import { useTableLogic } from '@/composables/useTableLogic'
import { computed, toRef } from 'vue'
import { useSystemTableLogic } from '@/composables/useSystemTableLogic'
import { useAllScopeTableLogic } from '@/composables/useAllScopeTableLogic'
import { mdiTrashCanOutline, mdiPencil } from '@mdi/js'

const props = defineProps<{
  search: string | undefined
  workspaceId?: string
  canEdit: Boolean
  scope?: 'workspace' | 'system' | 'all'
}>()

const { item, items, openEdit, openDelete, openDialog, onUpdate, onDelete } =
  props.scope === 'all'
    ? useAllScopeTableLogic(
        async (wsId: string) =>
          await hs.sensors.listAllItems({ workspace_id: [wsId] }),
        () => hs.sensors.listAllItems({ workspace_id: ['null'] }),
        hs.sensors.delete,
        Sensor,
        toRef(props, 'workspaceId')
      )
    : props.workspaceId
    ? useTableLogic(
        async (wsId: string) =>
          await hs.sensors.listAllItems({ workspace_id: [wsId] }),
        hs.sensors.delete,
        Sensor,
        toRef(props, 'workspaceId')
      )
    : useSystemTableLogic(
        () => hs.sensors.listAllItems({ workspace_id: ['null'] }),
        (id: string) => hs.sensors.delete(id),
        Sensor
      )

const headers = computed(() => {
  const base: {
    title: string
    key: string
    sortable?: boolean
    align?: 'end'
  }[] = [
    { title: 'Name', key: 'name' },
    { title: 'Method Type', key: 'methodType' },
    { title: 'Method Code', key: 'methodCode' },
    { title: 'UUID', key: 'id' },
  ]
  if (props.scope === 'all') base.push({ title: 'Scope', key: 'scope', sortable: false })
  base.push({ title: 'Actions', key: 'actions', sortable: false, align: 'end' })
  return base
})

const sortedItems = computed(() =>
  items.value.sort((a, b) => a.name.localeCompare(b.name))
)
</script>
