<template>
  <v-list class="pa-0">
    <v-list-item
      v-for="(datastream, index) of plottedDatastreams"
      :title="datastream.name"
      :base-color="qcDatastream == datastream ? COLORS[0] : COLORS[index + 1]"
      :active="qcDatastream == datastream"
    >
      <template #title="{ title }">
        <span :title="`${title}`">{{ title }}</span>
      </template>

      <template #prepend>
        <v-list-item-action start>
          <v-radio
            :disabled="isUpdating"
            density="comfortable"
            :model-value="qcDatastream == datastream"
            @click="setQcDatastream((qcDatastream = datastream))"
          ></v-radio>
          <v-btn
            :disabled="isUpdating"
            :icon="
              visibleDict[datastream.id] === false ? 'mdi-eye-off' : 'mdi-eye'
            "
            variant="flat"
            color="transparent"
            size="small"
            rounded
            @click="toggleVisibility(datastream)"
          ></v-btn>
        </v-list-item-action>
      </template>

      <template #append>
        <v-list-item-action end>
          <div class="ml-1" v-if="plottedDatastreams.length > 1">
            <v-btn
              :disabled="!index"
              icon="mdi-arrow-up"
              size="small"
              variant="text"
              rounded="true"
              color="default"
              title="Move up"
            ></v-btn>
            <v-btn
              :disabled="index >= plottedDatastreams.length - 1"
              icon="mdi-arrow-down"
              size="small"
              variant="text"
              rounded="true"
              color="default"
              title="Move down"
            ></v-btn>
          </div>
          <v-btn
            icon="mdi-close"
            size="small"
            variant="text"
            rounded="true"
            color="default"
            @click="toggleDatastream(datastream)"
            title="Remove from plot"
          ></v-btn>
        </v-list-item-action>
        <!-- <v-label>Editing...</v-label> -->
      </template>

      <template #subtitle> {{ datastream.valueCount }} Observations</template>
    </v-list-item>
  </v-list>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { COLORS, handleNewPlot } from '@/utils/plotting/plotly'
// import { Datastream } from '@/types'
import { usePlotlyStore } from '@/store/plotly'
const { updateOptions } = usePlotlyStore()
const { plotlyRef } = storeToRefs(usePlotlyStore())
// @ts-ignore no type definitions
import Plotly from 'plotly.js-dist'
import { Ref, ref, computed } from 'vue'
import { Datastream } from '@hydroserver/client'

const { plottedDatastreams, qcDatastream, loadingStates } =
  storeToRefs(useDataVisStore())
const { toggleDatastream } = useDataVisStore()
const visibleDict: Ref<{ [key: string]: boolean }> = ref({})

const setQcDatastream = async (datastream: Datastream) => {
  qcDatastream.value = datastream
  updateOptions()
  await handleNewPlot()
}

const isUpdating = computed(() =>
  Array.from(loadingStates.value.values()).some((isLoading) => isLoading)
)

const toggleVisibility = async (datastream: Datastream) => {
  const traceIndex = plotlyRef.value?.data.findIndex(
    (trace: any) => trace.id == datastream.id
  )
  if (traceIndex >= 0) {
    const isVisible = plotlyRef.value?.data[traceIndex].visible
    visibleDict.value[datastream.id] = !(
      isVisible === true || isVisible == undefined
    )
    await Plotly.restyle(
      plotlyRef.value,
      { visible: visibleDict.value[datastream.id] },
      [traceIndex]
    )
  }
}
</script>

<style scoped></style>
