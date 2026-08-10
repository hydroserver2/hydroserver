<template>
  <v-card>
    <v-toolbar flat color="primary">
      <v-card-title> {{ isEdit ? 'Edit' : 'Add' }} Method </v-card-title>
    </v-toolbar>
    <v-divider />

    <v-form
      @submit.prevent="onSubmit"
      ref="myForm"
      v-model="valid"
      validate-on="blur"
    >
      <v-card-text>
        <v-combobox
          v-model="item.type"
          :items="vocabularyStore.methodTypes"
          label="Type *"
          hide-details
          density="comfortable"
          :rules="rules.required"
          class="mb-4"
        />

        <v-text-field
          v-model="item.name"
          label="Name *"
          :rules="rules.requiredAndMaxLength255"
        />

        <v-text-field
          v-model="item.code"
          label="Code"
          :rules="rules.name"
        />

        <v-textarea
          v-model="item.description"
          label="Description *"
          rows="1"
          :rules="rules.requiredDescription"
        />

        <v-text-field
          v-model="item.definition"
          label="Definition"
          :rules="item.definition ? rules.urlFormat : []"
        />

        <v-text-field
          v-if="isInstrument"
          v-model="item.sensorModelManufacturer"
          label="Sensor Model Manufacturer"
          :rules="rules.name"
        />

        <v-text-field
          v-if="isInstrument"
          v-model="item.sensorModel"
          label="Sensor Model"
          :rules="rules.name"
        />

        <v-text-field
          v-if="isInstrument"
          v-model="item.sensorModelDefinition"
          label="Sensor Model Definition"
          :rules="item.sensorModelDefinition ? rules.urlFormat : []"
        />

        <v-divider />

        <v-card-actions>
          <v-spacer />
          <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
          <v-btn-primary type="submit">{{
            isEdit ? 'Update' : 'Save'
          }}</v-btn-primary>
        </v-card-actions>
      </v-card-text>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { VForm } from 'vuetify/components'
import { useFormLogic } from '@/composables/useFormLogic'
import { rules } from '@/utils/rules'
import { computed } from 'vue'
import hs, { Method } from '@hydroserver/client'
import { useVocabularyStore } from '@/composables/useVocabulary'

const props = defineProps<{
  method?: Method
  workspaceId?: string
}>()

const emit = defineEmits(['created', 'updated', 'close'])

const { item, isEdit, valid, myForm, uploadItem } = useFormLogic(
  hs.methods.create,
  hs.methods.update,
  Method,
  props.method || undefined
)
const vocabularyStore = useVocabularyStore()

const isInstrument = computed(
  () => item.value.type === 'Instrument Deployment'
)

async function onSubmit() {
  try {
    if (props.workspaceId) item.value.workspaceId = props.workspaceId
    const newItem = await uploadItem()
    if (!newItem) {
      if (isEdit.value) emit('close')
      return
    }
    if (isEdit.value) emit('updated', newItem)
    else emit('created', newItem.id)
  } catch (error) {
    console.error('Error uploading method', error)
  }
  emit('close')
}
</script>
