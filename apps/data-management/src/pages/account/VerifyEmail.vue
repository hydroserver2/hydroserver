<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" md="8">
        <v-card>
          <v-toolbar flat color="secondary">
            <v-card-title color="secondary"> Verify Your Email </v-card-title>
          </v-toolbar>

          <v-card-text v-if="verifying">
            Verifying your email address...
          </v-card-text>
          <v-card-text v-else-if="verified">
            Your email has been verified! You can now continue using
            HydroServer.
          </v-card-text>
          <v-card-text v-else-if="verificationError">
            <p class="text-error">Your email could not be verified.</p>
            <p>Please try resending or contact support.</p>
          </v-card-text>
          <v-card-text v-else>
            Before you continue, we need to verify the email address you
            provided for your account. We've sent an email with a verification
            code to
            {{ unverifiedEmail }}. Please enter the code below.
            <v-text-field
              v-model="verificationCode"
              label="Verification Code"
              type="text"
              :rules="rules.required"
              class="mt-4"
            />

            <v-row class="mt-2">
              <v-spacer />
              <v-col cols="auto">
                <v-btn
                  variant="outlined"
                  color="default"
                  :disabled="verifying || resending"
                  @click="logout"
                >
                  Cancel account creation
                </v-btn>
              </v-col>
              <v-col cols="auto">
                <v-btn :disabled="verifying || resending" @click="verifyCode">
                  Verify Code
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row justify="center">
      <v-col cols="12" md="8">
        <span class="mr-2">Didn't receive a verification email?</span>
        <v-btn
          :disabled="resending"
          color="primary"
          variant="text"
          @click="resend"
        >
          Resend Email
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Snackbar } from '@/utils/notifications'
import { rules } from '@/utils/rules'
import hs from '@hydroserver/client'

const router = useRouter()
const verifying = ref(false)
const verified = ref(false)
const verificationError = ref(false)
const verificationCode = ref('')
const resending = ref(false)

const unverifiedEmail = ref(hs.session.unverifiedEmail)

async function logout() {
  await hs.session.logout()
  await router.push({ name: 'Login' })
}

const verifyCode = async () => {
  if (!verificationCode.value) {
    Snackbar.error('Please enter the verification code.')
    return
  }

  try {
    verifying.value = true
    await hs.user.verifyEmailWithCode(verificationCode.value)
    verified.value = true
    Snackbar.success('Your email has been verified.')
    await router.push({ name: 'Sites' })
  } catch (e) {
    console.error('Error verifying email:', e)
    verificationError.value = true
  } finally {
    verifying.value = false
  }
}

async function resend() {
  try {
    resending.value = true
    await hs.user.sendVerificationEmail(unverifiedEmail.value)
    Snackbar.success('Verification email resent.')
  } catch (err) {
    console.error('Error sending verification email:', err)
    Snackbar.error('Failed to resend verification email.')
  } finally {
    resending.value = false
  }
}
</script>
