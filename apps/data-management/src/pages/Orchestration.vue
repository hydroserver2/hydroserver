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
      <OrchestrationWorkbench :workspace-id="selectedWorkspace.id" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import OrchestrationWorkbench from '@/components/Orchestration/OrchestrationWorkbench.vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { storeToRefs } from 'pinia'
import hs from '@hydroserver/client'
import WorkspaceToolbar from '@/components/Workspace/WorkspaceToolbar.vue'
import { useRoute } from 'vue-router'
import router from '@/router/router'

const workspaceStore = useWorkspaceStore()
const { selectedWorkspace, workspaces } = storeToRefs(workspaceStore)
const { setWorkspaces, setSelectedWorkspaceById } = workspaceStore

const route = useRoute()

const selectedWorkspaceIdFromQuery = computed(() => {
  const value = route.query.workspaceId
  return typeof value === 'string' && value.trim() ? value : null
})

const workspaceFetchCompleted = ref(false)

const routeToAccessDenied = async () => {
  await router.replace({
    name: 'AccessDenied',
    query: {
      from: route.fullPath,
    },
  })
}

const applyWorkspaceFromQuery = async () => {
  const workspaceId = selectedWorkspaceIdFromQuery.value
  if (!workspaceId) return true
  if (!workspaces.value.length && !workspaceFetchCompleted.value) return true

  const workspace = workspaces.value.find((ws) => ws.id === workspaceId)
  if (!workspace) {
    await routeToAccessDenied()
    return false
  }

  if (selectedWorkspace.value?.id !== workspace.id) {
    setSelectedWorkspaceById(workspace.id)
  }
  return true
}

watch(
  selectedWorkspaceIdFromQuery,
  async () => {
    await applyWorkspaceFromQuery()
  },
  { immediate: true }
)

watch(selectedWorkspace, async (workspace) => {
  if (!workspace?.id) return
  if (selectedWorkspaceIdFromQuery.value === workspace.id) return

  await router.replace({
    name: 'Orchestration',
    query: { ...route.query, workspaceId: workspace.id },
  })
})

onMounted(async () => {
  if (workspaces.value.length) {
    workspaceFetchCompleted.value = true
    await applyWorkspaceFromQuery()
    return
  }

  if (!(await applyWorkspaceFromQuery())) return

  try {
    const workspacesResponse = await hs.workspaces.listAllItems({
      is_associated: true,
      expand_related: true,
    })
    workspaceFetchCompleted.value = true
    setWorkspaces(workspacesResponse)
  } catch (error) {
    console.error('Error fetching workspaces', error)
  } finally {
    await applyWorkspaceFromQuery()
  }
})
</script>

<style scoped>
.orchestration-page {
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  height: calc(
    100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px)
  );
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
