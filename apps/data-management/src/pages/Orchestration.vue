<template>
  <div class="orchestration-page">
    <div class="orchestration-page-toolbar">
      <WorkspaceToolbar
        layout="orchestration"
        title="Job orchestration"
        hide-workspace-management
      />
    </div>

    <div v-if="!!selectedWorkspace" class="orchestration-page-body">
      <OrchestrationWorkbench />
    </div>
  </div>
</template>

<script setup lang="ts">
import OrchestrationWorkbench from '@/components/Orchestration/OrchestrationWorkbench.vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { storeToRefs } from 'pinia'
import WorkspaceToolbar from '@/components/Workspace/WorkspaceToolbar.vue'

const workspaceStore = useWorkspaceStore()
const { selectedWorkspace } = storeToRefs(workspaceStore)
</script>

<style scoped>
.orchestration-page {
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  height: calc(100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px));
  min-height: 0;
  overflow: hidden;
}

.orchestration-page-toolbar {
  flex-shrink: 0;
}

.orchestration-page-body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}
</style>
