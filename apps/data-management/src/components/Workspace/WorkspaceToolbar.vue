<template>
  <div v-if="layout === 'orchestration'" class="orchestration-header w-full">
    <div class="px-6 py-3">
      <v-row class="ma-0 gap-3" align="center" no-gutters>
        <v-col cols="auto">
          <h1 class="orchestration-header-title mb-0">
            {{ title || 'Job orchestration' }}
          </h1>
        </v-col>
        <v-spacer />
        <v-col cols="auto">
          <WorkspaceSelector />
        </v-col>
        <v-col v-if="!hideWorkspaceManagement" cols="12" sm="auto">
          <v-btn
            :to="{ name: 'Workspaces' }"
            rounded="lg"
            color="primary"
            variant="outlined"
            density="comfortable"
            class="text-none font-weight-regular"
          >
            Manage workspaces
          </v-btn>
        </v-col>
        <v-col v-if="$slots.actions" cols="12" sm="auto">
          <slot name="actions" />
        </v-col>
      </v-row>
    </div>
  </div>

  <div
    v-else-if="compactControls"
    class="flex items-center gap-2 min-w-0 flex-nowrap"
  >
    <WorkspaceSelector />
    <v-btn
      v-if="!hideWorkspaceManagement"
      :to="{ name: 'Workspaces' }"
      rounded="xl"
      color="secondary-darken-3"
      variant="outlined"
      density="comfortable"
    >
      Manage workspaces
    </v-btn>
  </div>

  <v-row v-else class="mt-0 mb-2" align="center">
    <v-col cols="auto">
      <WorkspaceSelector />
    </v-col>
    <v-col v-if="!hideWorkspaceManagement" cols="12" sm="auto">
      <v-btn
        :to="{ name: 'Workspaces' }"
        rounded="xl"
        color="secondary-darken-3"
        variant="outlined"
        density="comfortable"
      >
        Manage workspaces
      </v-btn>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import WorkspaceSelector from './WorkspaceSelector.vue'

const { compactControls, layout, title } = defineProps<{
  compactControls?: boolean
  layout?: 'default' | 'orchestration'
  title?: string
  hideWorkspaceManagement?: boolean
}>()
</script>

<style scoped>
.orchestration-header {
  background: #ffffff;
  border-bottom: 1px solid #ebebeb;
}

.orchestration-header-title {
  font-size: 22px;
  font-weight: 400;
  color: #1c1b1f;
  letter-spacing: 0;
  line-height: 1.2;
}
</style>
