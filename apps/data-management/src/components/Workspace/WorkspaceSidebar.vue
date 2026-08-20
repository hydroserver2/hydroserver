<template>
  <div class="workspace-sidebar">
    <div class="sidebar-header">
      <div class="sidebar-header-row">
        <span class="sidebar-title hs-label">Workspaces</span>
        <PermissionTooltip
          :has-permission="canCreate"
          message="You don't have permission to create a workspace."
        >
          <template #default>
            <button
              type="button"
              class="sidebar-add"
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
              class="sidebar-add"
              disabled
              aria-label="Add workspace"
              title="Add workspace"
            >
              <v-icon :icon="mdiPlus" size="16" />
            </button>
          </template>
        </PermissionTooltip>
      </div>

      <HsSearchInput
        v-model="search"
        class="sidebar-search"
        shape="pill"
        placeholder="Search workspaces…"
      />
    </div>

    <div class="hs-selection-list">
      <div
        v-for="workspace in filteredWorkspaces"
        :key="workspace.id"
        class="hs-selection-list__item hs-selection-list__item--with-actions"
        :class="{ 'is-selected': workspace.id === selectedId }"
        :data-testid="`workspace-list-item-${workspace.id}`"
      >
        <button
          type="button"
          class="hs-selection-list__body"
          :aria-label="`Select ${workspace.name} workspace`"
          :aria-current="workspace.id === selectedId ? 'true' : undefined"
          @click="emit('select', workspace.id)"
        >
          <div class="hs-selection-list__title hs-title">
            {{ workspace.name }}
          </div>
          <div class="hs-selection-list__meta hs-text-2xs">
            <span class="hs-selection-list__meta-text">
              {{ getUserRoleName(workspace) }} ·
              {{ workspace.isPrivate ? 'Private' : 'Public' }}
            </span>
          </div>
        </button>

        <span class="hs-selection-list__actions">
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
        </span>
      </div>

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
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Workspace } from '@hydroserver/client'
import { PermissionAction, PermissionResource } from '@hydroserver/client'
import { mdiPencil, mdiPlus, mdiTrashCanOutline } from '@mdi/js'
import HsSearchInput from '@/components/base/HsSearchInput.vue'
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

<style scoped>
.workspace-sidebar {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.sidebar-header {
  box-sizing: border-box;
  min-height: 93px;
  padding: var(--hs-space-12) var(--hs-space-16) var(--hs-space-8);
  border-bottom: 1px solid var(--hs-border);
}

.sidebar-header-row {
  display: flex;
  align-items: center;
}

.sidebar-header-row > :last-child {
  margin-left: auto;
}

.sidebar-title {
  color: var(--hs-text-secondary);
  letter-spacing: 0.7px;
  text-transform: uppercase;
}

.sidebar-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  color: rgb(var(--v-theme-on-primary));
  cursor: pointer;
  background: rgb(var(--v-theme-primary));
  border: 0;
  border-radius: var(--hs-radius-sm);
}

.sidebar-add:hover:not(:disabled) {
  background: rgb(var(--v-theme-primary-darken-1));
}

.sidebar-add:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.sidebar-add:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.sidebar-search {
  --hs-search-text: var(--hs-text-secondary);
  max-width: none;
  margin-top: var(--hs-space-8);
}
</style>
