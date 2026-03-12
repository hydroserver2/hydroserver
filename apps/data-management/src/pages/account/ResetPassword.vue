<template>
  <v-container class="d-flex align-center justify-center fill-height">
    <v-card class="login-card" width="30rem" v-if="passwordResetKey">
      <v-toolbar color="primary">
        <v-card-title>Reset Password</v-card-title>
      </v-toolbar>

      <v-form
        class="login-form"
        ref="myForm"
        @submit.prevent="resetPassword"
        v-model="valid"
      >
        <v-card-text>
          <v-text-field
            type="password"
            v-model="password"
            label="New Password"
            :rules="rules.password"
          ></v-text-field>
          <v-text-field
            type="password"
            v-model="confirmPassword"
            label="Confirm Password"
            :rules="rules.passwordMatch(password)"
          ></v-text-field>
        </v-card-text>

        <v-divider />

        <v-card-actions>
          <v-spacer />
          <v-btn-primary type="submit">Reset Password</v-btn-primary>
        </v-card-actions>
      </v-form>
    </v-card>

    <v-card width="30rem" v-else>
      <template v-if="!resetEmailSent">
        <v-toolbar color="primary">
          <v-card-title> Password reset request </v-card-title>
        </v-toolbar>

        <v-card-text class="pb-0">
          Forgot your password? Enter your email address below, and we'll email
          instructions for setting a new one.
        </v-card-text>

        <v-form @submit.prevent="onResetRequest">
          <v-card-text v-if="!resetEmailSent">
            <v-text-field v-model="email" label="Email" required type="email" />
          </v-card-text>
          <v-divider />
          <v-card-actions>
            <v-spacer />
            <v-btn-primary type="submit" color="primary">Submit</v-btn-primary>
          </v-card-actions>
        </v-form>
      </template>

      <v-card
        type="success"
        v-else
        class="d-flex flex-column align-center pa-4"
      >
        <v-card-text class="text-center">
          <v-icon color="success" size="80" :icon="mdiCheckCircle" />
          <p class="mt-4 text-body-1">
            A password reset email has been sent. Please check your inbox and
            follow the instructions to reset your password.
          </p>
        </v-card-text>
      </v-card>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { rules } from '@/utils/rules'
import hs from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { useRoute } from 'vue-router'
import router from '@/router/router'
import { mdiCheckCircle } from '@mdi/js'

const email = ref('')
const resetEmailSent = ref(false)
const route = useRoute()
const passwordResetKey = route.params.passwordResetKey?.toString() || null
const valid = ref(false)
const myForm = ref(null)
const password = ref('')
const confirmPassword = ref('')

const onResetRequest = async () => {
  const res = await hs.user.requestPasswordReset(email.value)
  if (res.status == 404)
    Snackbar.warn('No account was found for the email you specified')
  resetEmailSent.value = res.data
}

const resetPassword = async () => {
  if (!valid.value) return

  try {
    await hs.user.resetPassword(
      route.params.passwordResetKey.toString(),
      password.value
    )
    Snackbar.success('Password has been reset')
    await router.push({ name: 'Login' })
  } catch (error: any) {
    console.error('Error resetting password', error)
    Snackbar.error(error.message)
  }
}
</script>
