<template>
  <h2 class="hs-subheading privacy-title">Privacy</h2>

  <v-card-text>
    <small v-if="!canManage" class="hs-gate-note">
      <v-icon :icon="mdiLock" size="16" />
      <span>You don't have permission to change this workspace's privacy.</span>
    </small>

    <div class="privacy-card hs-table-card">
      <div
        class="hs-icon-tile"
        :class="isPrivate ? 'hs-icon-tile--private' : 'hs-icon-tile--public'"
      >
        <v-icon :icon="isPrivate ? mdiLock : mdiEarth" size="20" />
      </div>
      <div class="privacy-copy">
        <div class="privacy-copy-title hs-title">
          <span>Workspace is currently</span>
          <v-chip
            size="small"
            :color="isPrivate ? 'error' : 'success'"
            :data-testid="`workspace-privacy-status-${workspace.id}`"
          >
            {{ isPrivate ? 'Private' : 'Public' }}
          </v-chip>
        </div>
        <div class="privacy-copy-desc">
          <small>
            {{
              isPrivate
                ? 'Only you and collaborators can see this workspace and its related sites, datastreams and metadata.'
                : 'Visible to all users and guests of the system. Related sites and datastreams default to public but can be made private per-resource.'
            }}
          </small>
        </div>
      </div>
      <v-switch
        v-model="isPrivate"
        label="Make this workspace private"
        color="error"
        hide-details
        :loading="isUpdating"
        :disabled="!canManage || isUpdating"
        @update:model-value="togglePrivacy"
      />
    </div>
  </v-card-text>
</template>

<script setup lang="ts">
import hs, {
  PermissionAction,
  PermissionResource,
  Workspace,
} from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { computed, ref } from 'vue'
import { mdiHelpCircleOutline, mdiLock, mdiEarth } from '@mdi/js'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['privacy-updated'])

const { hasPermission } = useWorkspacePermissions()
const canManage = computed(() =>
  hasPermission(
    PermissionResource.Workspace,
    PermissionAction.Edit,
    props.workspace
  )
)

const isPrivate = ref(props.workspace.isPrivate)
const isUpdating = ref(false)

async function togglePrivacy() {
  isUpdating.value = true

  const res = await hs.workspaces.update({
    id: props.workspace.id,
    isPrivate: isPrivate.value,
  } as Workspace)

  if (res.ok) emits('privacy-updated', isPrivate.value)
  else {
    isPrivate.value = !isPrivate.value
    Snackbar.error(res.message)
    console.error('Error updating monitoringSite privacy', res)
  }

  isUpdating.value = false
}
</script>

<style scoped>
.privacy-title {
  margin-bottom: var(--hs-space-4);
}

/* Inline note explaining why the toggle below is disabled (permission-denied
   context). */
.hs-gate-note {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
  padding: var(--hs-space-12);
  margin-bottom: var(--hs-space-12);
  background: var(--hs-surface-muted);
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-md);
  color: var(--hs-text-secondary);
}
.hs-gate-note .v-icon {
  color: rgb(var(--v-theme-primary));
  flex-shrink: 0;
}

/* Small rounded icon tile leading the privacy-state row. Colors match the
   red/green private-public convention used on the datastream table's
   visibility icons, so the same state reads the same way everywhere. */
.hs-icon-tile {
  width: var(--hs-space-32);
  height: var(--hs-space-32);
  border-radius: var(--hs-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.hs-icon-tile--private {
  background: rgb(var(--v-theme-danger-bg));
  color: rgb(var(--v-theme-error));
}
.hs-icon-tile--public {
  background: var(--hs-surface-muted);
  color: rgb(var(--v-theme-success));
}

.privacy-card {
  display: flex;
  align-items: flex-start;
  gap: var(--hs-space-16);
  padding: var(--hs-space-20);
}
.privacy-copy {
  flex: 1;
  min-width: 0;
}
.privacy-copy-title {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
  color: var(--hs-text-primary);
  margin-bottom: var(--hs-space-6);
}
.privacy-copy-desc {
  color: var(--hs-text-secondary);
  line-height: 1.55;
  max-width: 520px;
}

@media (max-width: 600px) {
  .privacy-card {
    flex-wrap: wrap;
    padding: var(--hs-space-16);
  }
  .privacy-card .v-switch {
    flex-basis: 100%;
  }
}
</style>
