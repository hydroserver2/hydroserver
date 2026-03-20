<template>
  <v-card>
    <v-toolbar :color="workspaceId ? 'brown' : 'deep-orange-darken-4'">
      <v-card-title> {{ isEdit ? 'Edit' : 'Add' }} Unit </v-card-title>
    </v-toolbar>
    <v-divider />

    <v-form
      @submit.prevent="onSubmit"
      ref="myForm"
      v-model="valid"
      validate-on="blur"
    >
      <v-card-text v-if="item">
        <v-text-field
          v-model="item.name"
          label="Name *"
          :rules="rules.requiredAndMaxLength255"
        />
        <v-text-field
          v-model="item.symbol"
          label="Symbol *"
          :rules="rules.requiredAndMaxLength255"
        />
        <v-text-field
          v-model="item.definition"
          label="Definition *"
          :rules="rules.requiredDescription"
        />
        <v-text-field
          v-model="item.type"
          label="Unit Type *"
          :rules="rules.requiredAndMaxLength255"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
        <v-btn-primary type="submit">{{
          isEdit ? 'Update' : 'Save'
        }}</v-btn-primary>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { rules } from '@/utils/rules'
import { VForm } from 'vuetify/components'
import { useFormLogic } from '@/composables/useFormLogic'
import hs, { Unit } from '@hydroserver/client'

const props = defineProps<{
  unit?: Unit
  workspaceId?: string
}>()

const emit = defineEmits(['created', 'updated', 'close'])

const { item, isEdit, valid, myForm, uploadItem } = useFormLogic(
  hs.units.create,
  hs.units.update,
  Unit,
  props.unit || undefined
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
    console.error('Error uploading unit', error)
  }
  emit('close')
}
</script>
