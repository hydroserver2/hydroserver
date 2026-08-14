<template>
  <v-card color="blue-darken-4" variant="outlined">
    <v-card-text>
      <div class="mb-4">
        <div class="hs-text-md font-weight-bold text-primary-darken-1">
          {{ datastream.observedProperty.name }}
        </div>
        <div class="hs-text-2xs font-weight-medium text-grey-darken-1">
          Observed Property
        </div>
      </div>
      <!-- Processing Level -->
      <div class="mb-3">
        <div class="hs-text-md font-weight-medium">
          {{ datastream.processingLevel.definition }}
        </div>
        <div class="hs-text-2xs text-grey-darken-1">Processing Level</div>
      </div>

      <v-divider class="my-3" />

      <!-- Method and Sampled Medium (Less important) -->
      <div class="grid gap-y-2">
        <div class="flex items-center opacity-80">
          <span class="hs-text-sm font-weight-medium text-grey-darken-2 mr-2"
            >Method:</span
          >
          <span class="hs-text-sm">
            {{ datastream.method.name }}
          </span>
        </div>

        <div class="flex items-center opacity-80">
          <span class="hs-text-sm font-weight-medium text-grey-darken-2 mr-2"
            >Sampled Medium:</span
          >
          <span class="hs-text-sm">{{ datastream.sampledMedium }}</span>
        </div>

        <div class="flex items-center opacity-90">
          <span class="hs-text-sm font-weight-medium text-grey-darken-2 mr-2"
            >Identifier:</span
          >
          <span class="hs-text-sm">{{ datastream.id }}</span>
        </div>
      </div>

      <div v-if="addAggregation" class="flex items-center opacity-80">
        <span class="hs-text-sm font-weight-medium text-grey-darken-2 mr-2"
          >Aggregation Statistic:</span
        >
        <span class="hs-text-sm">{{ datastream?.aggregationStatistic }}</span>
      </div>

      <div v-if="addAggregation" class="flex items-center opacity-80">
        <span class="hs-text-sm font-weight-medium text-grey-darken-2 mr-2"
          >Aggregation Interval:</span
        >
        <span class="hs-text-sm">
          {{ datastream?.timeAggregationInterval }}
          {{ datastream?.timeAggregationIntervalUnit }}
        </span>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
const props = defineProps({
  datastream: {
    type: Object as () => any,
    required: true,
  },
  addAggregation: {
    type: Boolean,
    default: false,
  },
})
</script>
