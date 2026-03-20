<template>
  <v-data-table
    :items="userInformation"
    :items-per-page="-1"
    hide-default-header
    hide-default-footer
    density="compact"
    class="elevation-3 my-6 rounded-lg"
  >
    <template v-slot:top>
      <v-toolbar color="secondary" rounded="t-lg">
        <h5 class="text-h5 ml-4">User information</h5>
      </v-toolbar>
    </template>
    <template v-slot:item.icon="{ item }">
      <v-icon :icon="item?.icon"></v-icon>
    </template>
    <template v-slot:item.label="{ item }">
      <strong>{{ item?.label }}</strong>
    </template>
  </v-data-table>
</template>

<script setup lang="ts">
import { useUserStore } from '@/store/user'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { useHydroShare } from '@/composables/useHydroShare'
import {
  mdiAccount,
  mdiCardAccountDetails,
  mdiDatabase,
  mdiEmail,
  mdiLink,
  mdiMapMarker,
  mdiPhone,
} from '@mdi/js'

const { user } = storeToRefs(useUserStore())
const {
  isConnected: isHydroShareConnected,
  isConnectionEnabled: isHydroShareConnectionEnabled,
} = useHydroShare()

const userInformation = computed(() => {
  if (!user.value) return []

  return [
    {
      icon: mdiAccount,
      label: 'Name',
      value: `${user.value.firstName} ${user.value.middleName || ''} ${
        user.value.lastName
      }`,
    },
    { icon: mdiEmail, label: 'Email', value: user.value.email },
    {
      icon: mdiMapMarker,
      label: 'Address',
      value: user.value.address,
    },
    { icon: mdiPhone, label: 'Phone', value: user.value.phone },
    { icon: mdiCardAccountDetails, label: 'Type', value: user.value.type },
    { icon: mdiLink, label: 'Link', value: user.value.link },
    isHydroShareConnectionEnabled.value
      ? {
          icon: mdiDatabase,
          label: 'HydroShare account',
          value:
            isHydroShareConnected.value === true
              ? 'Connected'
              : 'Not Connected',
        }
      : null,
  ].filter(Boolean)
})
</script>
