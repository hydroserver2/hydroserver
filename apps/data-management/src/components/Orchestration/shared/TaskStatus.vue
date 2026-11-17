<template>
  <v-chip :color="chipColor" density="compact" class="ma-0 pa-2">
    {{ status }}
  </v-chip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StatusType } from '@hydroserver/client'
import { taskStatusColor } from '@/utils/orchestration/taskStatusColors'

interface Props {
  status: StatusType
}
const props = defineProps<Props>()

const chipColor = computed(() => taskStatusColor(props.status))
</script>
