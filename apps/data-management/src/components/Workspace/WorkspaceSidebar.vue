<template>
  <HsSelectionSidebar
    v-model="search"
    title="Workspaces"
    search-placeholder="Search workspaces…"
  >
    <template #actions>
      <PermissionTooltip
        :has-permission="canCreate"
        message="You don't have permission to create a workspace."
      >
        <template #default>
          <button
            type="button"
            class="hs-sidebar-action"
            aria-label="Add workspace"
            title="Add workspace"
            @click="emit('create')"
          >
            <v-icon :icon="mdiPlus" size="16" />
          </button>
        </template>
        <template #denied>
          <button
            type="button"
            class="hs-sidebar-action"
            disabled
            aria-label="Add workspace"
            title="Add workspace"
          >
            <v-icon :icon="mdiPlus" size="16" />
          </button>
        </template>
      </PermissionTooltip>
    </template>

    <HsSelectionListItem
      v-for="workspace in filteredWorkspaces"
      :key="workspace.id"
      :title="workspace.name"
      :selected="workspace.id === selectedId"
      :aria-label="`Select ${workspace.name} workspace`"
      :data-testid="`workspace-list-item-${workspace.id}`"
      @select="emit('select', workspace.id)"
    >
      <template #metadata>
        {{ getUserRoleName(workspace) }} ·
        {{ workspace.isPrivate ? 'Private' : 'Public' }}
      </template>

      <template #actions>
        <button
          type="button"
          class="hs-selection-list__action"
          :disabled="!canEditWorkspace(workspace)"
          :title="canEditWorkspace(workspace) ? '' : EDIT_DENIED_MESSAGE"
          :aria-label="`Edit ${workspace.name}`"
          :data-testid="`workspace-edit-${workspace.id}`"
          @click.stop="emit('edit', workspace)"
        >
          <v-icon :icon="mdiPencil" size="15" />
        </button>
        <button
          type="button"
          class="hs-selection-list__action hs-selection-list__action--danger"
          :disabled="!canDeleteWorkspace(workspace)"
          :title="canDeleteWorkspace(workspace) ? '' : DELETE_DENIED_MESSAGE"
          :aria-label="`Delete ${workspace.name}`"
          :data-testid="`workspace-delete-${workspace.id}`"
          @click.stop="emit('delete', workspace)"
        >
          <v-icon :icon="mdiTrashCanOutline" size="15" />
        </button>
      </template>
    </HsSelectionListItem>

    <div
      v-if="workspaces.length && !filteredWorkspaces.length"
      class="hs-selection-list__empty hs-text-sm"
    >
      No matching workspaces.
    </div>
    <div
      v-else-if="!workspaces.length"
      class="hs-selection-list__empty hs-text-sm"
    >
      No workspaces yet.
    </div>
  </HsSelectionSidebar>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Workspace } from '@hydroserver/client'
import { PermissionAction, PermissionResource } from '@hydroserver/client'
import { mdiPencil, mdiPlus, mdiTrashCanOutline } from '@mdi/js'
import HsSelectionListItem from '@/components/base/HsSelectionListItem.vue'
import HsSelectionSidebar from '@/components/base/HsSelectionSidebar.vue'
import PermissionTooltip from '@/components/PermissionTooltip.vue'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'

const props = defineProps<{
  workspaces: Workspace[]
  selectedId: string
  canCreate: boolean
}>()

const emit = defineEmits<{
  create: []
  select: [workspaceId: string]
  edit: [workspace: Workspace]
  delete: [workspace: Workspace]
}>()

const EDIT_DENIED_MESSAGE = 'You do not have permission to edit this workspace.'
const DELETE_DENIED_MESSAGE =
  'You do not have permission to delete this workspace.'

const { getUserRoleName, hasPermission } = useWorkspacePermissions()
const search = ref('')

const filteredWorkspaces = computed(() => {
  const term = search.value.trim().toLocaleLowerCase()
  if (!term) return props.workspaces
  return props.workspaces.filter((workspace) =>
    workspace.name.toLocaleLowerCase().includes(term)
  )
})

function canEditWorkspace(workspace: Workspace) {
  return hasPermission(
    PermissionResource.Workspace,
    PermissionAction.Edit,
    workspace
  )
}

function canDeleteWorkspace(workspace: Workspace) {
  return hasPermission(
    PermissionResource.Workspace,
    PermissionAction.Delete,
    workspace
  )
}
</script>
