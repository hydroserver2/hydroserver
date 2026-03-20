<template>
  <v-container>
    <AccountForm :has-cancel-button="false" is-edit is-complete-signup>
      <template v-slot:header>
        <v-toolbar color="secondary">
          <v-card-title align="center">
            Successfully authenticated -
            <span class="opacity-90">
              Just a few more details and your account will be all set.
            </span>
          </v-card-title>
        </v-toolbar>
      </template>
    </AccountForm>
  </v-container>
</template>

<script setup lang="ts">
import AccountForm from '@/components/account/AccountForm.vue'
</script>
