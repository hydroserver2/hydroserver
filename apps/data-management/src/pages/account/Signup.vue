<template>
  <v-container>
    <v-row justify="center" align="center" class="mt-10">
      <v-col cols="12" sm="8" lg="6">
        <AccountForm :has-cancel-button="false">
          <template v-slot:header>
            <v-card-title align="center" class="mb-2 signup-title">
              Sign Up
            </v-card-title>
            <v-card-text align="center" class="my-2">
              Note that all provided information besides your password will be
              publicly viewable. This helps with communication and data
              integrity.
            </v-card-text>
          </template>
        </AccountForm>
      </v-col>
    </v-row>

    <v-row justify="center" class="mt-6">
      <span class="mr-2">Already have an account?</span>
      <router-link
        to="/login"
        class="text-[rgb(var(--v-theme-primary))] underline underline-offset-2 hover:decoration-2 focus:decoration-2"
      >
        Sign In
      </router-link>
    </v-row>

    <OAuth />

    <div class="mb-10"></div>
  </v-container>
</template>

<script setup lang="ts">
import AccountForm from '@/components/account/AccountForm.vue'
import OAuth from '@/components/account/OAuth.vue'
</script>
