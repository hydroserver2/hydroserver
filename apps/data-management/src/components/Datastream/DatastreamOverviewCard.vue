<template>
  <v-card color="blue-darken-4" variant="outlined">
    <v-card-text>
      <div class="mb-4">
        <div class="text-h6 font-weight-bold text-primary-darken-1">
          {{ datastream.observedProperty.name }}
        </div>
        <div class="text-caption font-weight-medium text-grey-darken-1">
          Observed Property
        </div>
      </div>
      <!-- Processing Level -->
      <div class="mb-3">
        <div class="text-subtitle-1 font-weight-medium">
          {{ datastream.processingLevel.definition }}
        </div>
        <div class="text-caption text-grey-darken-1">Processing Level</div>
      </div>

      <v-divider class="my-3" />

      <!-- Sensor and Sampled Medium (Less important) -->
      <div class="grid gap-y-2">
        <div class="flex items-center opacity-80">
          <span class="text-body-2 font-weight-medium text-grey-darken-2 mr-2"
            >Sensor:</span
          >
          <span class="text-body-2">
            {{ datastream.sensor.name }}
          </span>
        </div>

        <div class="flex items-center opacity-80">
          <span class="text-body-2 font-weight-medium text-grey-darken-2 mr-2"
            >Sampled Medium:</span
          >
          <span class="text-body-2">{{ datastream.sampledMedium }}</span>
        </div>

        <div class="flex items-center opacity-90">
          <span class="text-body-2 font-weight-medium text-grey-darken-2 mr-2"
            >Identifier:</span
          >
          <span class="text-body-2">{{ datastream.id }}</span>
        </div>
      </div>

      <div v-if="addAggregation" class="flex items-center opacity-80">
        <span class="text-body-2 font-weight-medium text-grey-darken-2 mr-2"
          >Aggregation Statistic:</span
        >
        <span class="text-body-2">{{ datastream?.aggregationStatistic }}</span>
      </div>

      <div v-if="addAggregation" class="flex items-center opacity-80">
        <span class="text-body-2 font-weight-medium text-grey-darken-2 mr-2"
          >Aggregation Interval:</span
        >
        <span class="text-body-2">
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
