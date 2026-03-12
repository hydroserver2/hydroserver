<template>
  <v-card>
    <v-toolbar color="blue-darken-4">
      <v-card-title>
        {{ isEdit ? 'Edit' : 'Create' }} API key
        <span v-if="isEdit" class="opacity-80">- {{ item.name }}</span>
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
          label="Name *"
          :rules="rules.requiredAndMaxLength150"
        />
        <v-text-field v-model="item.description" label="Description" />
        <v-select
          v-model="item.role"
          :items="roles"
          label="New API key's role *"
          item-title="name"
          :return-object="true"
          variant="outlined"
          :rules="required"
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
import { required, rules } from '@/utils/rules'
import { VForm } from 'vuetify/components'
import { useFormLogic } from '@/composables/useFormLogic'
import hs, { ApiKey, CollaboratorRole } from '@hydroserver/client'

const props = defineProps<{
  apiKey?: ApiKey
  workspaceId: string
  roles: CollaboratorRole[]
}>()

const emit = defineEmits(['created', 'updated', 'close'])

const { item, isEdit, valid, myForm, uploadItem } = useFormLogic(
  hs.workspaces.createApiKey,
  hs.workspaces.updateApiKey,
  ApiKey,
  props.apiKey || undefined
)

async function onSubmit() {
  try {
    item.value.workspaceId = props.workspaceId
    const newItem = await uploadItem()
    if (!newItem) {
      if (isEdit.value) emit('close')
      return
    }
    if (isEdit.value) emit('updated', newItem)
    else emit('created', newItem)
  } catch (error) {
    console.error('Error uploading API key', error)
  }
  emit('close')
}
</script>
