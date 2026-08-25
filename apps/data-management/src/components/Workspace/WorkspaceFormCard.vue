<template>
  <v-card>
    <v-toolbar flat color="primary">
      <v-card-title class="hs-subheading">
        {{ isEdit ? 'Edit' : 'Add' }} workspace
      </v-card-title>
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
        <v-checkbox
          v-model="item.isPrivate"
          label="Make this workspace private"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
        <v-btn-primary
          type="submit"
          :loading="isSubmitting"
          :disabled="isSubmitting"
          >{{ isEdit ? 'Update' : 'Save' }}</v-btn-primary
        >
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { rules } from '@/utils/rules'
import { VForm } from 'vuetify/components'
import hs, { Workspace } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { computed, ref } from 'vue'

const props = defineProps({ workspace: Object as () => Workspace })
const emit = defineEmits(['created', 'updated', 'close'])

const item = ref(JSON.parse(JSON.stringify(props.workspace ?? new Workspace())))
const isEdit = computed(() => !!props.workspace || undefined)
const valid = ref(false)
const myForm = ref<VForm>()
const isSubmitting = ref(false)

async function onSubmit() {
  if (isSubmitting.value) return
  await myForm.value?.validate()
  if (!valid.value) return
  isSubmitting.value = true

  try {
    const res = isEdit.value
      ? await hs.workspaces.update(item.value, props.workspace)
      : await hs.workspaces.create(item.value)

    if (!res.ok) {
      console.error('Error uploading workspace', res)
      Snackbar.error(res.message || 'Unable to save the workspace.')
      return
    }

    const updatedOrCreated = isEdit.value ? 'updated' : 'created'
    Snackbar.success(`Workspace ${updatedOrCreated}`)
    emit(`${updatedOrCreated}`, res.data)
    emit('close')
  } catch (error) {
    console.error('Error uploading workspace', error)
    Snackbar.error('Unable to save the workspace.')
  } finally {
    isSubmitting.value = false
  }
}
</script>
