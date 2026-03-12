<template>
  <v-card>
    <v-card-title class="headline">Confirm Account Deletion</v-card-title>

    <v-divider></v-divider>

    <v-card-text>
      Are you sure you want to delete your account? This action will permanently
      remove all your information from the system including all sites,
      datastreams, and observations you have primary ownership of, user
      information, and preferences. This action cannot be undone.
    </v-card-text>

    <v-card-text v-if="ownedWorkspaces.length > 0">
      The following is a list of the workspaces you have ownership of that will
      be deleted with your account. If you have collaborators for these
      workspaces, we strongly recommend transferring ownership to one of them
      before deleting your account. Additionally, you have the option to store
      your site data in HydroShare or download your data before deleting your
      account.
    </v-card-text>
    <v-card-text v-for="workspace in ownedWorkspaces" class="py-0">
      {{ workspace.name }}
    </v-card-text>

    <v-card-text>
      Please type the following text to confirm deletion:
      <strong> delete my account and data </strong>
      <v-form>
        <v-text-field
          v-model="deleteInput"
          solo
          @keydown.enter.prevent="deleteAccount"
        ></v-text-field>
      </v-form>
    </v-card-text>

    <v-divider></v-divider>

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn-cancel @click="cancelDeletion">Cancel</v-btn-cancel>
      <v-btn-delete @click="deleteAccount">Delete</v-btn-delete>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import hs, { Thing } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'
import router from '@/router/router'

const { ownedWorkspaces } = storeToRefs(useWorkspaceStore())

const things = ref<Thing[]>([])

const emit = defineEmits(['delete', 'close'])
const deleteInput = ref('')

async function deleteAccount() {
  if (deleteInput.value.toLowerCase() !== 'delete my account and data') {
    Snackbar.error("input doesn't match")
    return
  }
  try {
    emit('close')
    await hs.user.delete()
    await hs.session.logout()
    await router.push({ name: 'Login' })
    Snackbar.info('Your account has been deleted')
  } catch (error) {
    console.error('Error deleting account', error)
  }
}

function cancelDeletion() {
  deleteInput.value = ''
  emit('close')
}

onMounted(
  async () =>
    (things.value = await hs.things.listAllItems({ order_by: ['name'] }))
)
</script>
