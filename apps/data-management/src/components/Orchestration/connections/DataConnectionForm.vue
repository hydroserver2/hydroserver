<template>
  <StickyForm v-if="loaded">
    <template #header>
      <p class="ml-6 font-weight-bold">
        {{ isEdit ? 'Edit' : 'Create a new' }} data connection
        <span v-if="isEdit" class="opacity-80"
          >- {{ formDataConnection?.name }}</span
        >
      </p>
    </template>

    <v-form
      @submit.prevent="onSubmit"
      ref="myForm"
      v-model="valid"
      validate-on="input"
      class="d-flex flex-column flex-grow-1"
    >
      <div class="form-body">
        <p class="font-weight-bold mb-2 required-label">
          Name your data connection
        </p>
        <v-text-field
          v-model="formDataConnection.name"
          label="Data connection name"
          :rules="rules.requiredAndMaxLength255"
          density="compact"
        />

        <ExtractorForm ref="extractorRef" />
        <TransformerForm ref="transformerRef" />
        <TimezoneForm ref="timezoneRef" />

        <div class="ma-2">
          <v-switch
            v-model="advancedFeaturesEnabled"
            color="primary"
            density="compact"
            hide-details
            label="Advanced features"
          />

          <div v-if="advancedFeaturesEnabled" class="advanced-features-body">
            <p class="font-weight-bold mb-2">Authentication header</p>
            <div class="auth-header-grid">
              <v-combobox
                v-model="formDataConnection.authHeaderName"
                :items="authHeaderNameOptions"
                label="Header name"
                placeholder="Authorization"
                clearable
                autocomplete="off"
                name="data-connection-auth-header-name"
                density="compact"
                :rules="authHeaderNameRules"
              />
              <v-text-field
                v-model="formDataConnection.authHeaderValue"
                type="text"
                label="Header value"
                placeholder="Bearer abc123"
                clearable
                autocomplete="off"
                autocapitalize="off"
                spellcheck="false"
                name="data-connection-auth-header-value"
                density="compact"
                :class="{
                  'auth-header-value-field--masked': !showAuthHeaderValue,
                }"
                :rules="authHeaderValueRules"
                :append-inner-icon="showAuthHeaderValue ? mdiEyeOff : mdiEye"
                @click:append-inner="showAuthHeaderValue = !showAuthHeaderValue"
              />
            </div>

            <p class="font-weight-bold mb-2">Email notifications</p>
            <v-combobox
              v-model="notificationRecipientEmails"
              v-model:search="notificationRecipientInput"
              :items="[]"
              label="Notification recipients"
              placeholder="Type an email address and press Enter"
              multiple
              clearable
              hide-no-data
              hide-selected
              density="compact"
              :rules="notificationRecipientRules"
              :error-messages="
                notificationRecipientInputError
                  ? [notificationRecipientInputError]
                  : []
              "
              @keydown.enter.prevent="addNotificationRecipient"
              @keydown.tab="addNotificationRecipient"
              @blur="addNotificationRecipient"
            >
              <template #selection="{ item, index }">
                <v-chip
                  size="small"
                  color="blue-grey"
                  variant="tonal"
                  rounded
                  closable
                  class="mr-1 mb-1 max-w-full"
                  @click:close="removeNotificationRecipient(index)"
                >
                  <span class="truncate">{{ item.title }}</span>
                </v-chip>
              </template>
            </v-combobox>
          </div>
        </div>
      </div>
    </v-form>

    <template #actions>
      <v-spacer />
      <v-btn-cancel @click="emit('close')"> Cancel </v-btn-cancel>
      <v-btn-primary type="button" @click="onSubmit"> Save </v-btn-primary>
    </template>
  </StickyForm>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { VForm } from 'vuetify/components'
import { storeToRefs } from 'pinia'
import StickyForm from '@/components/Forms/StickyForm.vue'
import { rules } from '@/utils/rules'
import { useDataConnectionStore } from '@/store/dataConnection'
import { useWorkspaceStore } from '@/store/workspaces'
import ExtractorForm from './extractors/ExtractorForm.vue'
import TransformerForm from './transformers/TransformerForm.vue'
import TimezoneForm from '@/components/Orchestration/connections/timestamps/TimezoneForm.vue'
import hs, { DataConnection } from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { ensureNotificationSchedule } from '@/utils/orchestration/dataConnectionNotifications'
import { mdiEye, mdiEyeOff } from '@mdi/js'

const props = defineProps<{
  dataConnection?: DataConnection
}>()

const emit = defineEmits(['created', 'updated', 'close'])

const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
const { dataConnection: formDataConnection } = storeToRefs(
  useDataConnectionStore()
)

const isEdit = computed(() => !!props.dataConnection)
const valid = ref(false)
const myForm = ref<VForm>()

const extractorRef = ref<any>(null)
const transformerRef = ref<any>(null)
const timezoneRef = ref<any>(null)

const loaded = ref(false)
const isSubmitting = ref(false)
const advancedFeaturesEnabled = ref(false)
const showAuthHeaderValue = ref(false)
const notificationRecipientInput = ref('')
const notificationRecipientInputError = ref('')

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const authHeaderNameOptions = ['Authorization', 'X-API-Key']

const toRecipientString = (value: unknown) => {
  if (typeof value === 'string') return value.trim()
  if (value && typeof value === 'object' && 'title' in value) {
    return `${(value as { title?: string }).title ?? ''}`.trim()
  }
  return `${value ?? ''}`.trim()
}

const normalizeNotificationRecipients = (values: readonly unknown[]) => {
  const normalized: string[] = []
  const seen = new Set<string>()

  for (const value of values) {
    const email = toRecipientString(value)
    if (!email) continue

    const dedupeKey = email.toLowerCase()
    if (seen.has(dedupeKey)) continue

    seen.add(dedupeKey)
    normalized.push(email)
  }

  return normalized
}

const isValidNotificationRecipient = (value: string) => emailPattern.test(value)

const notificationRecipientEmails = computed<string[]>({
  get: () =>
    (formDataConnection.value as any).notification?.recipientEmails ?? [],
  set: (value) => {
    const dc = formDataConnection.value as any
    if (!dc.notification) dc.notification = {}
    dc.notification.recipientEmails = normalizeNotificationRecipients(value)
  },
})

const notificationRecipientRules = [
  (value: string[] = []) =>
    value.every(isValidNotificationRecipient) ||
    'All notification recipient emails must be valid.',
]

const authHeaderNameRules = [
  (value: string | null) =>
    !advancedFeaturesEnabled.value ||
    !!toRecipientString(value) ||
    !toRecipientString(formDataConnection.value.authHeaderValue) ||
    'Header name is required when a header value is provided.',
  (value: string | null) =>
    toRecipientString(value).length <= 255 || 'Maximum 255 characters allowed.',
]

const authHeaderValueRules: Array<(value: string | null) => true | string> = []

function hasAdvancedFeatures(dataConnection?: DataConnection) {
  if (!dataConnection) return false

  return !!(
    toRecipientString(dataConnection.authHeaderName) ||
    toRecipientString(dataConnection.authHeaderValue) ||
    (dataConnection as any).notification?.recipientEmails?.length
  )
}

function resetFormState(dataConnection?: DataConnection) {
  formDataConnection.value = dataConnection ?? new DataConnection()
  advancedFeaturesEnabled.value = hasAdvancedFeatures(formDataConnection.value)
  showAuthHeaderValue.value = false
  notificationRecipientInput.value = ''
  notificationRecipientInputError.value = ''
}

function addNotificationRecipient() {
  const email = notificationRecipientInput.value.trim().replace(/,+$/, '')
  if (!email) {
    notificationRecipientInputError.value = ''
    notificationRecipientInput.value = ''
    return true
  }

  if (!isValidNotificationRecipient(email)) {
    notificationRecipientInputError.value = 'Email must be valid.'
    return false
  }

  notificationRecipientEmails.value = [
    ...notificationRecipientEmails.value,
    email,
  ]
  notificationRecipientInput.value = ''
  notificationRecipientInputError.value = ''
  return true
}

function removeNotificationRecipient(index: number) {
  notificationRecipientEmails.value = notificationRecipientEmails.value.filter(
    (_, recipientIndex) => recipientIndex !== index
  )
}

watch(notificationRecipientInput, () => {
  if (notificationRecipientInputError.value) {
    notificationRecipientInputError.value = ''
  }
})

watch(
  () => props.dataConnection,
  (dataConnection) => resetFormState(dataConnection),
  { immediate: true }
)

watch(advancedFeaturesEnabled, () => {
  notificationRecipientInputError.value = ''
})

async function validate() {
  const validExtractor = await extractorRef.value.validate()
  const validTransformer = await transformerRef.value.validate()
  const validTimezone = await timezoneRef.value?.validate()
  return validExtractor && validTransformer && (validTimezone ?? true)
}

async function onSubmit() {
  const etlValid = await validate()
  if (!etlValid) return

  if (advancedFeaturesEnabled.value && !addNotificationRecipient()) return

  isSubmitting.value = true

  await myForm.value?.validate()
  if (!valid.value) {
    isSubmitting.value = false
    return false
  }

  formDataConnection.value.workspace = selectedWorkspace.value
  normalizeAdvancedFields(formDataConnection.value)
  ensureNotificationSchedule(formDataConnection.value)

  const body = {
    ...formDataConnection.value,
    workspaceId: selectedWorkspace.value?.id,
  }
  const res = isEdit.value
    ? await hs.dataConnections.update(formDataConnection.value)
    : await hs.dataConnections.create(body as any)

  if (res.ok) {
    if (isEdit.value) {
      emit('updated', res.data)
      Snackbar.success('Updated data connection')
    } else {
      emit('created', res.data.id)
      Snackbar.success('Created data connection')
    }
    emit('close')
  } else {
    Snackbar.error(res.message)
    console.error(res)
  }

  isSubmitting.value = false
}

function normalizeAdvancedFields(dataConnection: DataConnection) {
  if (!advancedFeaturesEnabled.value) {
    dataConnection.authHeaderName = null
    dataConnection.authHeaderValue = null
    dataConnection.notification = null
    return
  }

  const authHeaderName = `${dataConnection.authHeaderName ?? ''}`.trim()
  const authHeaderValue = `${dataConnection.authHeaderValue ?? ''}`.trim()

  dataConnection.authHeaderName = authHeaderName || null
  dataConnection.authHeaderValue = authHeaderValue || null

  const recipientEmails =
    dataConnection.notification?.recipientEmails.filter(Boolean) ?? []

  if (recipientEmails.length === 0) {
    dataConnection.notification = null
  } else if (dataConnection.notification) {
    dataConnection.notification.recipientEmails = recipientEmails
  }
}

onMounted(async () => {
  loaded.value = true
})
</script>

<style scoped>
.form-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: visible;
  padding: 16px 24px;
  scrollbar-gutter: stable both-edges;
}

.advanced-features-body {
  margin-top: 12px;
}

.auth-header-grid {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(220px, 2fr);
  gap: 12px;
}

.auth-header-value-field--masked :deep(input) {
  -webkit-text-security: disc;
}

@media (max-width: 640px) {
  .auth-header-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
}
</style>
