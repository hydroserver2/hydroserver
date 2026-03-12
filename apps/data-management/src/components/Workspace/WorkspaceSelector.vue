<template>
  <v-select
    v-model="selectedWorkspace"
    hint="Selected Workspace"
    :items="workspaces"
    item-title="name"
    :return-object="true"
    variant="plain"
    hide-details
    class="workspace-selector"
  >
    <template v-slot:item="{ props, item }">
      <v-list-item
        v-bind="props"
        :title="item.raw.name"
        :subtitle="`Your role: ${getUserRoleName(item.raw)}`"
      />
    </template>

    <template #selection="{ item }">
      <span v-if="item" class="block whitespace-nowrap" :title="item.raw.name">
        <span class="opacity-60"> Selected workspace: </span>
        {{ item.raw.name }}
      </span>
      <span v-else class="block whitespace-nowrap">Select a workspace</span>
    </template>
  </v-select>
</template>

<script setup lang="ts">
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useWorkspaceStore } from '@/store/workspaces'
import { storeToRefs } from 'pinia'

const { selectedWorkspace, workspaces } = storeToRefs(useWorkspaceStore())
const { getUserRoleName } = useWorkspacePermissions()
</script>

<style scoped>
.workspace-selector {
  width: fit-content;
  min-width: max-content;
}

.workspace-selector :deep(.v-input__control),
.workspace-selector :deep(.v-field),
.workspace-selector :deep(.v-field__field),
.workspace-selector :deep(.v-field__input) {
  width: fit-content;
  min-width: max-content;
}

.workspace-selector :deep(.v-select__selection) {
  overflow: visible;
}
</style>
