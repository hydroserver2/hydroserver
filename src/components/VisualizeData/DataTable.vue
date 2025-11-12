<template>
  <div class="d-flex">
    <v-data-table-virtual
      :headers="headers"
      :items="virtualData"
      height="400"
      item-value="datetime"
      fixed-header
      class="flex-grow-1"
      :loading="isUpdating"
      disable-sort
      :row-props="getRowProps"
    >
      <template #item.actions="{ index }">
        <v-checkbox
          color="primary"
          hide-details
          :model-value="selectedData?.includes(index)"
          @update:model-value="onSelectChange($event, index)"
        ></v-checkbox>
      </template>

      <template #item.datetime="{ index }">
        {{ formatDate(new Date(selectedSeries?.data.dataX[index])) }}
      </template>

      <template #item.value="{ index }">
        {{ formatNumber(selectedSeries?.data.dataY[index]) }}
      </template>
    </v-data-table-virtual>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// @ts-ignore no type definitions
import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { formatDate } from '@uwrl/qc-utils'
import { useDataSelection } from '@/composables/useDataSelection'

const { isUpdating, selectedSeries } = storeToRefs(usePlotlyStore())
const { selectedData } = storeToRefs(useDataVisStore())
const { dispatchSelection } = useDataSelection()

const headers = [
  { title: '', align: 'start', key: 'actions', width: '50px' },
  { title: 'Datetime', align: 'start', key: 'datetime' },
  { title: 'Value', align: 'end', key: 'value' },
]

const virtualData = computed(() => {
  return new Array(selectedSeries?.value?.data.dataX.length).fill(null)
})

const onSelectChange = (isSelected: boolean, index: number) => {
  if (isSelected) {
    if (!selectedData.value) {
      selectedData.value = []
    }
    selectedData.value?.push(index)
  } else {
    const pos = selectedData.value?.indexOf(index)
    if (pos !== undefined && pos >= 0) {
      selectedData.value?.splice(pos, 1)
    }
  }

  selectedData.value?.sort((a, b) => a - b)

  // dispatchSelection(selectedData.value || [])
}

const getRowProps = (data: any) => {
  return {
    class: {
      'bg-grey-lighten-4': selectedData.value?.includes(
        data.internalItem.index
      ),
    },
  }
}

function formatNumber(num: any) {
  return parseFloat(num.toFixed(4)) // Converts back to number, removing trailing .00 for integers
}
</script>

<style scoped></style>
