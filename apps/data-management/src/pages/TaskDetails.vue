<template>
  <component
    v-if="detailsComponent && resolvedTaskId"
    :is="detailsComponent"
    :task-id="resolvedTaskId"
    :run-id="resolvedRunId"
    :embedded="embedded"
    @close="$emit('close')"
    @deleted="$emit('deleted')"
    @updated="$emit('updated')"
  />
  <div v-else class="loading">Loading...</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import hs from '@hydroserver/client'
import IngestionTaskDetails from '@/components/Orchestration/IngestionTaskDetails.vue'
import AggregationTaskDetails from '@/components/Orchestration/AggregationTaskDetails.vue'
import ExpressionTaskDetails from '@/components/Orchestration/ExpressionTaskDetails.vue'
import DerivationTaskDetails from '@/components/Orchestration/DerivationTaskDetails.vue'
import RatingCurveTaskDetails from '@/components/Orchestration/RatingCurveTaskDetails.vue'
import QualityTaskDetails from '@/components/Orchestration/QualityTaskDetails.vue'
import type { TaskKind } from '@/components/Orchestration/workbench/orchestrationTabs'

const props = withDefaults(
  defineProps<{
    taskId?: string | null
    taskKind?: TaskKind | null
    runId?: string | null
    embedded?: boolean
  }>(),
  {
    taskId: null,
    taskKind: null,
    runId: null,
    embedded: false,
  }
)

defineEmits(['close', 'deleted', 'updated'])

const route = useRoute()
const productType = ref<string | null>(null)

const resolvedTaskId = computed(() => {
  if (props.taskId) return props.taskId
  const param = route.params.id
  return Array.isArray(param) ? (param[0] ?? '') : `${param ?? ''}`
})

const resolvedRunId = computed(() => {
  if (props.runId) return props.runId
  const value = route.query.runId
  return typeof value === 'string' ? value : null
})

const resolvedKind = computed<TaskKind>(() => {
  if (props.taskKind) return props.taskKind
  const value = route.query.taskKind
  if (value === 'dataProduct' || value === 'monitoring') return value
  return 'etl'
})

const detailsComponent = computed(() => {
  if (resolvedKind.value === 'etl') return IngestionTaskDetails
  if (resolvedKind.value === 'monitoring') return QualityTaskDetails
  if (productType.value === 'aggregation') return AggregationTaskDetails
  if (productType.value === 'expression') return ExpressionTaskDetails
  if (productType.value === 'derivation') return DerivationTaskDetails
  if (productType.value === 'ratingCurve') return RatingCurveTaskDetails
  return null
})

async function resolveProductType() {
  productType.value = null
  if (resolvedKind.value !== 'dataProduct' || !resolvedTaskId.value) return
  const response = await hs.dataProductTasks.get(resolvedTaskId.value, {
    expand_related: true,
  })
  const task = response.data as any
  if (task?.aggregationTransformations?.length)
    productType.value = 'aggregation'
  else if (task?.expressionTransformations?.length)
    productType.value = 'expression'
  else if (task?.compositeExpressionTransformations?.length)
    productType.value = 'derivation'
  else if (task?.ratingCurveTransformations?.length)
    productType.value = 'ratingCurve'
}

onMounted(resolveProductType)
watch([resolvedTaskId, resolvedKind], resolveProductType)
</script>

<style scoped>
.loading {
  padding: 40px 20px;
  text-align: center;
  color: #5f5a67;
}
</style>
