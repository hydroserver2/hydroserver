<template>
  <component
    v-if="detailsComponent && resolvedTaskId"
    :is="detailsComponent"
    :task-id="resolvedTaskId"
    :run-id="resolvedRunId"
    :embedded="embedded"
    :initial-task="initialTaskForComponent"
    @close="$emit('close')"
    @deleted="$emit('deleted')"
    @updated="$emit('updated')"
  />
  <div v-else class="loading">Loading...</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import IngestionTaskDetails from '@/components/Orchestration/ingestion/IngestionTaskDetails.vue'
import AggregationTaskDetails from '@/components/Orchestration/data-products/AggregationTaskDetails.vue'
import ExpressionTaskDetails from '@/components/Orchestration/data-products/ExpressionTaskDetails.vue'
import DerivationTaskDetails from '@/components/Orchestration/data-products/DerivationTaskDetails.vue'
import RatingCurveTaskDetails from '@/components/Orchestration/data-products/RatingCurveTaskDetails.vue'
import QualityTaskDetails from '@/components/Orchestration/monitoring/QualityTaskDetails.vue'
import {
  normalizeOrchestrationTaskDetailType,
  type OrchestrationTaskDetailType,
} from '@/composables/orchestration/useOrchestrationRouteState'

const props = withDefaults(
  defineProps<{
    taskId?: string | null
    detailType?: OrchestrationTaskDetailType | null
    runId?: string | null
    embedded?: boolean
    initialTask?: any
  }>(),
  {
    taskId: null,
    detailType: null,
    runId: null,
    embedded: false,
    initialTask: null,
  }
)

defineEmits(['close', 'deleted', 'updated'])

const route = useRoute()

const resolvedTaskId = computed(() => {
  if (props.taskId) return props.taskId
  const value = route.query.task_id
  if (Array.isArray(value)) return value[0] ?? ''
  return typeof value === 'string' ? value : ''
})

const resolvedRunId = computed(() => {
  if (props.runId) return props.runId
  const value = route.query.run_id
  return typeof value === 'string' ? value : null
})

const resolvedDetailType = computed(
  () =>
    props.detailType ??
    normalizeOrchestrationTaskDetailType(route.meta.orchestrationTaskDetail)
)

const detailsComponent = computed(() => {
  if (resolvedDetailType.value === 'ingestion') return IngestionTaskDetails
  if (resolvedDetailType.value === 'aggregation') return AggregationTaskDetails
  if (resolvedDetailType.value === 'expression') return ExpressionTaskDetails
  if (resolvedDetailType.value === 'derivation') return DerivationTaskDetails
  if (resolvedDetailType.value === 'rating-curve') return RatingCurveTaskDetails
  if (resolvedDetailType.value === 'quality') return QualityTaskDetails
  return null
})
const initialTaskForComponent = computed(() => props.initialTask)
</script>

<style scoped>
.loading {
  padding: 40px 20px;
  text-align: center;
  color: #5f5a67;
}
</style>
