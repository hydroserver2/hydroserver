<template>
  <v-card rounded>
    <v-container>
      <v-card-title>Update series style</v-card-title>

      <v-form @submit.prevent="onSubmit" ref="myForm" validate-on="blur">
        <v-card-text>
          <v-select
            :items="lineTypes"
            label="Select Line Style"
            v-model="selectedLineType"
          />

          <v-select
            :items="symbols"
            label="Select Symbol"
            v-model="selectedSymbol"
          />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
          <v-btn rounded variant="outlined" type="submit">Update</v-btn>
        </v-card-actions>
      </v-form>
    </v-container>
  </v-card>
</template>

<script setup lang="ts">
import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'
import { onMounted, ref } from 'vue'

const { graphSeriesArray } = storeToRefs(usePlotlyStore())

const props = defineProps({ datastreamId: { type: String, required: true } })
const emit = defineEmits(['submit', 'close'])

const selectedLineType = ref()
const selectedSymbol = ref()

const lineTypes = ['solid', 'dashed', 'dotted', 'none']
const symbols = [
  'circle',
  'rect',
  'roundRect',
  'triangle',
  'diamond',
  'pin',
  'arrow',
  'none',
]

onMounted(() => {
  void graphSeriesArray.value.find((s) => s.id === props.datastreamId)
})

function onSubmit() {
  const type =
    selectedLineType.value === 'none' ? undefined : selectedLineType.value
  const symbol =
    selectedSymbol.value === 'none' ? undefined : selectedSymbol.value

  emit('submit', {
    lineStyle: { type, width: !!type ? 1 : 0 },
    symbol,
    showSymbol: !!symbol,
  })
  emit('close')
}
</script>
