<template>
  <v-container class="mt-10">
    <v-row justify="center" align="center" class="mt-10">
      <v-col cols="12" sm="8" md="6">
        <v-card class="login-card">
          <v-card-title align="center" class="login-title">Log in</v-card-title>
          <v-divider class="my-2"></v-divider>
          <v-form
            class="login-form"
            @submit.prevent="formLogin"
            v-model="valid"
          >
            <v-card-text>
              <v-text-field
                class="mb-4 email-input"
                label="Email *"
                autofocus
                v-model="email"
                :rules="rules.email"
                type="email"
                name="email"
                validate-on="blur"
              ></v-text-field>
              <v-text-field
                class="mb-4 password-input"
                label="Password *"
                :rules="rules.required"
                v-model="password"
                type="password"
                name="password"
              ></v-text-field>
            </v-card-text>
            <v-divider class="login-divider"></v-divider>
            <v-card-actions class="text-body-1 signup-link-section">
              <v-spacer></v-spacer>
              <v-btn-primary
                :loading="loading"
                class="login-button mr-4"
                :disabled="!valid"
                type="submit"
                >Log in</v-btn-primary
              >
            </v-card-actions>
          </v-form>
        </v-card>
      </v-col>
    </v-row>

    <v-row
      justify="center"
      class="mt-6"
      v-if="disableAccountCreation !== 'true'"
    >
      <span class="mr-2">Don't have an account?</span>
      <router-link to="/sign-up" class="light-text signup-link"
        >Sign Up</router-link
      >
    </v-row>

    <OAuth />

    <v-row justify="center" class="my-10">
      <router-link to="/reset-password" class="light-text forgot-password-link"
        >Forgot your password?</router-link
      >
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { rules } from '@/utils/rules'
import OAuth from '@/components/account/OAuth.vue'
import { Snackbar } from '@uwrl/qc-utils'
import router from '@/router/router'
import { useRoute } from 'vue-router'
import hs from '@hydroserver/client'
import { useUserStore } from '@/store/user'
import { useWorkspaceStore } from '@/store/workspaces'
import { storeToRefs } from 'pinia'

const email = ref('')
const password = ref('')
const valid = ref(false)
const loading = ref(false)
const disableAccountCreation =
  import.meta.env.VITE_APP_DISABLE_ACCOUNT_CREATION || 'false'

const { user } = storeToRefs(useUserStore())
const route = useRoute()

const formLogin = async () => {
  if (!valid) return
  loading.value = true
  const res = await hs.session.login(email.value, password.value)
  if (res.ok) {
    const resUser = res.data?.account
    if (resUser) {
      user.value = resUser
      // Seed the workspace list so the post-login destination (Home,
      // picker, or a deep-linked route) has workspace context without
      // waiting for App.vue's watcher to fire.
      try {
        await useWorkspaceStore().loadWorkspaces()
      } catch (err) {
        console.error('Failed to load workspaces after login', err)
      }
      Snackbar.success('You have logged in!')
      const nextQuery = typeof route.query.next === 'string' ? route.query.next : null
      if (nextQuery) {
        await router.push(nextQuery.startsWith('/') ? nextQuery : { name: nextQuery })
      } else {
        await router.push({ name: 'Home' })
      }
    }
  } else {
    if (hs.session.inEmailVerificationFlow) {
      console.info('Email not verified. Redirecting to verify email page.')
      Snackbar.info('Email not verified. Redirecting to verify email page.')
      hs.session.unverifiedEmail = email.value
      await router.push({ name: 'VerifyEmail' })
    } else {
      if (res.status === 400) {
        Snackbar.warn('No active account found with the given credentials.')
      }
      console.error('Error logging in.', res)
    }
  }
  loading.value = false
}
</script>
