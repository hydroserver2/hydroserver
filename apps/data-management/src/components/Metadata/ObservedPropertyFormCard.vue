<template>
  <v-card>
    <v-toolbar flat color="primary">
      <v-card-title>
        {{ isEdit ? 'Edit' : 'Add' }} Observed Property
      </v-card-title>
    </v-toolbar>
    <v-divider />

    <v-form
      @submit.prevent="onSubmit"
      ref="myForm"
      v-model="valid"
      validate-on="blur"
    >
      <v-card-text>
        <v-text-field
          v-model="item.name"
          hide-details
          label="Name"
          :rules="rules.requiredAndMaxLength255"
          @update:modelValue="handleNameUpdated"
          class="pb-4 required-label"
        />

        <v-text-field
          v-model="item.definition"
          label="Definition"
          :rules="[...rules.maxLength(2000), ...(item.definition ? rules.urlFormat : [])]"
        />

        <v-textarea
          v-model="item.description"
          class="required-label"
          label="Description"
          :rules="rules.required"
        ></v-textarea>

        <v-combobox
          :items="vocabularyStore.observedPropertyTypes"
          v-model="item.type"
          class="required-label"
          label="Variable Type"
          :rules="rules.requiredAndMaxLength255"
        />

        <v-text-field
          v-model="item.code"
          label="Code"
          :rules="rules.maxLength(255)"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
        <v-btn-dialog-action type="submit">{{
          isEdit ? 'Update' : 'Save'
        }}</v-btn-dialog-action>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { VForm } from 'vuetify/components'
import { useFormLogic } from '@/composables/useFormLogic'
import { rules } from '@/utils/rules'
import { OPNameTypes } from '@/config/vocabularies'
import hs, { ObservedProperty } from '@hydroserver/client'
import { useVocabularyStore } from '@/composables/useVocabulary'

const OPNames = Object.keys(OPNameTypes)

const props = defineProps<{
  observedProperty?: ObservedProperty
  workspaceId?: string
}>()

const emit = defineEmits(['created', 'updated', 'close'])

const { item, isEdit, valid, myForm, uploadItem } = useFormLogic(
  hs.observedProperties.create,
  hs.observedProperties.update,
  ObservedProperty,
  props.observedProperty || undefined
)
const vocabularyStore = useVocabularyStore()

const handleNameUpdated = () => {
  const name = item.value.name
  if (name && OPNames.includes(name)) {
    item.value.definition = ''
    item.value.description = `${OPNameTypes[name].definition}. ${OPNameTypes[name].description}`
  }
}

async function onSubmit() {
  try {
    if (props.workspaceId) item.value.workspaceId = props.workspaceId
    const newItem = await uploadItem()
    if (!newItem) return
    if (isEdit.value) emit('updated', newItem)
    else emit('created', newItem.id)
  } catch (error) {
    console.error('Error uploading observed property', error)
    return
  }
  emit('close')
}
</script>
