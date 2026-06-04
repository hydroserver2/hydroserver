<template>
  <v-form ref="localForm" v-model="isValid" validate-on="input">
    <v-card
      color="blue-grey-darken-2"
      class="mt-4"
      variant="outlined"
      rounded="lg"
    >
      <v-toolbar title="Loader" color="blue-grey-darken-2" />
      <v-card-text>
        Data will be loaded into HydroServer. No additional configuration
        needed.
      </v-card-text>
    </v-card>
  </v-form>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { VForm } from 'vuetify/lib/components/index.mjs'

const localForm = ref<VForm>()
const isValid = ref(true)

async function validate() {
  await localForm.value?.validate()
  return isValid.value
}

defineExpose({ validate })
</script>
