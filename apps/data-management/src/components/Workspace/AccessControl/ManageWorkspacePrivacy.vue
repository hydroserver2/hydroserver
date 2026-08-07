<template>
  <h6 class="text-h6 privacy-title">Privacy</h6>

  <v-card-text>
    <div v-if="!canManage" class="hs-gate-note">
      <v-icon :icon="mdiLock" size="16" />
      <span
        >You do not have permission to change this workspace's privacy.</span
      >
    </div>

    <div class="privacy-card hs-table-card">
      <div
        class="hs-icon-tile"
        :class="isPrivate ? 'hs-icon-tile--private' : 'hs-icon-tile--public'"
      >
        <v-icon :icon="isPrivate ? mdiLock : mdiEarth" size="20" />
      </div>
      <div class="privacy-copy">
        <div class="privacy-copy-title">
          <span>Workspace is currently</span>
          <v-chip
            size="small"
            :color="isPrivate ? 'red-darken-2' : 'green'"
            text-color="white"
            :data-testid="`workspace-privacy-status-${workspace.id}`"
          >
            {{ isPrivate ? 'Private' : 'Public' }}
          </v-chip>
        </div>
        <div class="privacy-copy-desc">
          {{
            isPrivate
              ? 'Only you and collaborators can see this workspace and its related sites, datastreams and metadata.'
              : 'Visible to all users and guests of the system. Related sites and datastreams default to public but can be made private per-resource.'
          }}
        </div>
      </div>
      <v-switch
        v-model="isPrivate"
        label="Make this workspace private"
        color="red-darken-2"
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
  margin-bottom: 4px;
}

/* Inline note explaining why the toggle below is disabled (permission-denied
   context). */
.hs-gate-note {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 13px;
  margin-bottom: 14px;
  background: #fbfaf7;
  border: 1px solid #ece6da;
  border-radius: 8px;
  font-size: 12.5px;
  color: #8a7a5c;
}
.hs-gate-note .v-icon {
  color: #b8924a;
  flex-shrink: 0;
}

/* Small rounded icon tile leading the privacy-state row. Colors match the
   red/green private-public convention used on the datastream table's
   visibility icons, so the same state reads the same way everywhere. */
.hs-icon-tile {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.hs-icon-tile--private {
  background: #fdecea;
  color: #c62828;
}
.hs-icon-tile--public {
  background: #e8f5e9;
  color: #2e7d32;
}

.privacy-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 20px;
}
.privacy-copy {
  flex: 1;
  min-width: 0;
}
.privacy-copy-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #1c1b1f;
  margin-bottom: 6px;
}
.privacy-copy-desc {
  font-size: 12.5px;
  color: #6b7280;
  line-height: 1.55;
  max-width: 520px;
}

@media (max-width: 600px) {
  .privacy-card {
    flex-wrap: wrap;
    padding: 16px;
  }
  .privacy-card .v-switch {
    flex-basis: 100%;
  }
}
</style>
