<template>
  <v-form ref="localForm" v-model="isValid" validate-on="input">
    <v-card class="mt-4" color="green-darken-4" variant="outlined" rounded="lg">
      <v-toolbar color="green">
        <v-card-title>Payload</v-card-title>
        <v-spacer />
        <v-select
          class="mx-4"
          v-model="payloadType"
          :items="['CSV', 'JSON']"
          label="Payload type"
          density="compact"
          rounded="lg"
          hide-details
          max-width="200px"
          variant="outlined"
        />
      </v-toolbar>

      <JSONTransformerForm v-if="payloadType === 'JSON'" />
      <CSVTransformerForm v-else-if="payloadType === 'CSV'" />
    </v-card>
  </v-form>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDataConnectionStore } from '@/store/dataConnection'
import { storeToRefs } from 'pinia'
import JSONTransformerForm from './JSONTransformerForm.vue'
import CSVTransformerForm from './CSVTransformerForm.vue'
import { VForm } from 'vuetify/lib/components/index.mjs'

const localForm = ref<VForm>()
const isValid = ref(true)

async function validate() {
  await localForm.value?.validate()
  return isValid.value
}

defineExpose({ validate })

const { dataConnection } = storeToRefs(useDataConnectionStore())

const payloadType = computed({
  get: () => dataConnection.value.payload.type,
  set: (newType: 'CSV' | 'JSON') => {
    if (newType === 'CSV') {
      dataConnection.value.payload = { type: 'CSV', timestampKey: '' }
    } else {
      dataConnection.value.payload = { type: 'JSON', timestampKey: '' }
    }
  },
})
</script>
