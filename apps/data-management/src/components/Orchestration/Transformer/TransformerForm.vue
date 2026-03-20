<template>
  <v-form ref="localForm" v-model="isValid" validate-on="input">
    <v-card class="mt-4" color="green-darken-4" variant="outlined" rounded="lg">
      <v-toolbar color="green">
        <v-card-title>Transformer configurations</v-card-title>
        <v-spacer />
        <v-select
          class="mx-4"
          v-model="transformer.type"
          :items="TRANSFORMER_OPTIONS"
          label="Type"
          density="compact"
          rounded="lg"
          :prepend-inner-icon="mdiWeb"
          hide-details
          max-width="250px"
          variant="outlined"
        />
      </v-toolbar>

      <JSONTransformerForm v-if="transformer.type === 'JSON'" />
      <CSVTransformerForm v-else-if="transformer.type === 'CSV'" />
    </v-card>
  </v-form>
</template>

<script setup lang="ts">
import JSONTransformerForm from './JSONTransformerForm.vue'
import { ref, watch } from 'vue'
import { useDataConnectionStore } from '@/store/dataConnection'

import { storeToRefs } from 'pinia'
import CSVTransformerForm from './CSVTransformerForm.vue'
import {
  switchTransformer,
  TRANSFORMER_OPTIONS,
  TransformerConfig,
} from '@hydroserver/client'
import { VForm } from 'vuetify/lib/components/index.mjs'
import { mdiWeb } from '@mdi/js'

const localForm = ref<VForm>()

async function validate() {
  await localForm.value?.validate()
  return isValid.value
}

defineExpose({ validate })

const {
  transformer,
  dataConnection,
  isTransformerValid: isValid,
} = storeToRefs(useDataConnectionStore())

const savedTransformer: TransformerConfig = JSON.parse(
  JSON.stringify(transformer.value)
)

watch(
  () => transformer.value.type,
  (newType) => {
    if (savedTransformer.type === newType)
      transformer.value = JSON.parse(JSON.stringify(savedTransformer))
    else switchTransformer(dataConnection.value, newType)
  }
)
</script>
