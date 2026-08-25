<template>
  <v-card>
    <v-toolbar flat color="primary">
      <v-card-title class="hs-subheading">
        {{ isEdit ? 'Edit' : 'Create' }} service account
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
          v-model="selectedRole"
          :items="roles"
          data-testid="service-account-role"
          label="Service account's role *"
          item-title="name"
          :return-object="true"
          variant="outlined"
          :rules="required"
          :disabled="isEdit && !canAssignRole"
          :hint="
            isEdit && !canAssignRole
              ? `You don't have permission to change collaborator roles.`
              : undefined
          "
          :persistent-hint="isEdit && !canAssignRole"
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
import { required, rules } from '@/utils/rules'
import { VForm } from 'vuetify/components'
import { ref } from 'vue'
import { useFormLogic } from '@/composables/useFormLogic'
import { Snackbar } from '@/utils/notifications'
import hs, {
  ServiceAccount,
  CollaboratorRole,
  ApiResponse,
} from '@hydroserver/client'

type ServiceAccountRow = ServiceAccount & { role?: CollaboratorRole }

const props = defineProps<{
  serviceAccount?: ServiceAccountRow
  workspaceId: string
  roles: CollaboratorRole[]
  canAssignRole: boolean
}>()

const emit = defineEmits(['created', 'updated', 'close'])
const isSubmitting = ref(false)

const selectedRole = ref<CollaboratorRole | undefined>(
  props.serviceAccount?.role
)

async function createItem(
  newAccount: ServiceAccount
): Promise<ApiResponse<ServiceAccount>> {
  return hs.workspaces.createServiceAccount(newAccount, selectedRole.value!.id)
}

async function updateItem(
  newAccount: ServiceAccount,
  originalAccount: ServiceAccount
): Promise<ApiResponse<ServiceAccount>> {
  const res = await hs.workspaces.updateServiceAccount(
    newAccount,
    originalAccount
  )
  if (!res.ok) return res

  if (
    props.canAssignRole &&
    selectedRole.value &&
    selectedRole.value.id !== props.serviceAccount?.role?.id
  ) {
    const roleRes = await hs.workspaces.updateCollaboratorRole(
      props.workspaceId,
      res.data.email,
      selectedRole.value.id
    )
    if (!roleRes.ok) return roleRes
  }
  return res
}

const { item, isEdit, valid, myForm, uploadItem } = useFormLogic(
  createItem,
  updateItem,
  ServiceAccount,
  props.serviceAccount || undefined
)

async function onSubmit() {
  if (isSubmitting.value) return
  isSubmitting.value = true
  try {
    item.value.workspaceId = props.workspaceId
    const newItem = await uploadItem()
    if (!valid.value) return
    if (!newItem) {
      Snackbar.error(
        isEdit.value
          ? 'Unable to update service account.'
          : 'Unable to create service account.'
      )
      return
    }
    const row: ServiceAccountRow = { ...newItem, role: selectedRole.value }
    if (isEdit.value) emit('updated', row)
    else emit('created', row)
    emit('close')
  } catch (error) {
    console.error('Error uploading service account', error)
    Snackbar.error(
      isEdit.value
        ? 'Unable to update service account.'
        : 'Unable to create service account.'
    )
  } finally {
    isSubmitting.value = false
  }
}
</script>
