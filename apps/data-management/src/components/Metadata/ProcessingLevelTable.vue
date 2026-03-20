<template>
  <v-data-table-virtual
    :headers="ProcLevelHeaders"
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
    <ProcessingLevelFormCard
      :processing-level="item"
      @close="openEdit = false"
      @updated="onUpdate"
      v-bind="{
        ...(workspaceId ? { 'workspace-id': workspaceId } : {}),
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
import hs, { ProcessingLevel } from '@hydroserver/client'
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
          await hs.processingLevels.listAllItems({ workspace_id: [wsId] }),
        hs.processingLevels.delete,
        ProcessingLevel,
        toRef(props, 'workspaceId')
      )
    : useSystemTableLogic(
        () => hs.processingLevels.listAllItems(),
        (id: string) => hs.processingLevels.delete(id),
        ProcessingLevel
      )

const ProcLevelHeaders = [
  { title: 'Code', key: 'code' },
  { title: 'Definition', key: 'definition' },
  { title: 'Explanation', key: 'explanation' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
] as const

const sortedItems = computed(() =>
  items.value.sort((a, b) => a.code.localeCompare(b.code))
)
</script>
