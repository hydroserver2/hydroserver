<template>
  <v-card>
    <v-toolbar flat color="primary">
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
          class="required-label"
          label="Name"
          :rules="rules.requiredAndMaxLength255"
        />
        <v-text-field
          v-model="item.symbol"
          class="required-label"
          label="Symbol"
          :rules="rules.requiredAndMaxLength255"
        />
        <v-text-field
          v-model="item.definition"
          class="required-label"
          label="Definition"
          :rules="rules.requiredDescription"
        />
        <v-text-field
          v-model="item.type"
          class="required-label"
          label="Unit Type"
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
