<template>
  <div class="service-accounts-section" data-testid="service-accounts-section">
    <v-alert
      v-if="loadError"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-3"
    >
      <div class="d-flex align-center ga-2">
        <span>{{ loadError }}</span>
        <v-spacer />
        <v-btn variant="text" size="small" @click="reloadData">Retry</v-btn>
      </div>
    </v-alert>
    <v-progress-linear v-if="isLoading" indeterminate class="mb-2" />

    <v-card-text v-if="showNewKey && newKey">
      <v-alert
        type="success"
        border="start"
        elevation="2"
        variant="tonal"
        class="mb-4"
      >
        Your service account API key has been generated. Please copy it and
        store it somewhere safe — you won’t be able to see it again after
        leaving this page.
      </v-alert>

      <v-sheet
        color="surface-muted"
        class="pa-4 rounded d-flex align-center justify-space-between"
        border
      >
        <span class="text-mono text-wrap break-all">{{ newKey.key }}</span>
        <v-btn
          :icon="mdiContentCopy"
          variant="text"
          color="grey-darken-2"
          @click="copyKey(newKey.key)"
          aria-label="Copy service account API key"
        />
      </v-sheet>
    </v-card-text>

    <div class="hs-table-tools">
      <div class="workspace-table-search">
        <v-icon
          :icon="mdiMagnify"
          size="16"
          class="workspace-table-search-icon"
        />
        <div
          class="workspace-table-search-highlight hs-text-sm"
          aria-hidden="true"
        >
          <span
            v-for="(segment, index) in highlightSegments"
            :key="index"
            :class="segment.cls"
            >{{ segment.text }}</span
          >
        </div>
        <input
          ref="searchInputEl"
          v-model="search"
          placeholder="Search service accounts…"
          class="workspace-table-search-input hs-text-sm"
          aria-label="Search service accounts"
          autocomplete="off"
          spellcheck="false"
          role="combobox"
          aria-autocomplete="list"
          :aria-expanded="!!activeSuggestion"
          @input="onSearchInput"
          @click="syncCaret"
          @keyup="syncCaret"
          @keydown="onSearchKeydown"
          @focus="onSearchFocus"
          @blur="onSearchBlur"
        />
      </div>

      <v-btn
        :icon="mdiHelpCircleOutline"
        variant="text"
        size="small"
        color="grey-darken-2"
        title="About service accounts"
        aria-label="Toggle service account help"
        :aria-expanded="showServiceAccountHelp"
        @click="showServiceAccountHelp = !showServiceAccountHelp"
      />

      <div class="hs-table-actions">
        <PermissionTooltip
          :has-permission="canCreate"
          message="You don't have permission to create service accounts for this workspace."
        >
          <template #default>
            <v-btn-secondary variant="flat" @click="openCreate = true">
              Create service account
            </v-btn-secondary>
          </template>
          <template #denied>
            <v-btn-secondary variant="flat" disabled>
              Create service account
            </v-btn-secondary>
          </template>
        </PermissionTooltip>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="activeSuggestion && activeSuggestion.items.length"
        class="workspace-search-suggestions"
        :style="suggestionStyle"
        role="listbox"
      >
        <div class="workspace-search-suggestions-title">
          {{ activeSuggestion.type === 'key' ? 'Filter by…' : 'Role values' }}
        </div>
        <button
          v-for="(item, index) in activeSuggestion.items"
          :key="item"
          type="button"
          class="workspace-search-suggestion"
          :class="{
            'workspace-search-suggestion--active': index === suggestionIndex,
          }"
          role="option"
          :aria-selected="index === suggestionIndex"
          @mousedown.prevent="applySuggestion(item)"
        >
          {{ item }}{{ activeSuggestion.type === 'key' ? ':' : '' }}
        </button>
      </div>
    </Teleport>

    <p v-if="showServiceAccountHelp" class="service-accounts-help-text">
      <small>
        Service accounts provide remote systems with a controlled set of
        permissions. A service account can collaborate on other workspaces after
        it is created.
      </small>
    </p>

    <v-card class="hs-table-card service-accounts-table-card" flat>
      <v-table
        class="service-accounts-table"
        height="100%"
        fixed-header
      >
        <thead>
          <tr>
            <th>
              <div class="service-account-header-filters">
                <v-menu
                  :close-on-content-click="false"
                  location="bottom start"
                  attach="body"
                >
                  <template #activator="{ props: menuProps }">
                    <v-btn
                      v-bind="menuProps"
                      variant="text"
                      size="small"
                      class="service-account-filter-button"
                      :class="{
                        'service-account-filter-button--active':
                          selectedRoles.length,
                      }"
                      :append-icon="mdiChevronDown"
                      :aria-label="`Filter by role${selectedRoles.length ? ` (${selectedRoles.length} selected)` : ''}`"
                    >
                      Role
                      <span v-if="selectedRoles.length" class="filter-count">
                        {{ selectedRoles.length }}
                      </span>
                    </v-btn>
                  </template>
                  <v-list class="service-account-filter-menu" density="compact">
                    <div class="service-account-filter-title">
                      Filter by role
                    </div>
                    <v-text-field
                      v-model="roleFilterSearch"
                      class="service-account-filter-search"
                      placeholder="Filter roles"
                      :prepend-inner-icon="mdiMagnify"
                      variant="outlined"
                      density="compact"
                      hide-details
                      clearable
                    />
                    <v-list-item
                      v-for="role in filteredRoles"
                      :key="role"
                      @click="toggleRole(role)"
                    >
                      <template #prepend>
                        <v-checkbox
                          :model-value="selectedRoles.includes(role)"
                          hide-details
                          density="compact"
                          :aria-label="`Role: ${role}`"
                          @click.stop="toggleRole(role)"
                        />
                      </template>
                      <v-list-item-title>{{ role }}</v-list-item-title>
                    </v-list-item>
                    <v-list-item
                      v-if="selectedRoles.length"
                      class="filter-clear-item"
                      @click="selectedRoles = []"
                    >
                      <v-list-item-title>Clear filter</v-list-item-title>
                    </v-list-item>
                    <div v-if="!filteredRoles.length" class="filter-empty">
                      No roles found
                    </div>
                  </v-list>
                </v-menu>
              </div>
            </th>
            <th class="text-right" style="width: 190px">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="serviceAccountItem in filteredItems"
            :key="serviceAccountItem.id"
            :data-testid="`service-account-row-${serviceAccountItem.id}`"
          >
            <td>
              <div class="service-account-name font-weight-medium">
                {{ serviceAccountItem.name }}
              </div>
              <div class="hs-text-sm text-medium-emphasis">
                {{ serviceAccountItem.role?.name || 'No role' }}
              </div>
            </td>
            <td class="text-right">
              <v-btn
                :icon="mdiRefresh"
                variant="text"
                size="small"
                class="hs-table-icon-action"
                color="grey-darken-2"
                :disabled="!canEdit"
                :aria-label="`Regenerate ${serviceAccountItem.name}`"
                @click="onOpenRegenerateDialog(serviceAccountItem)"
              />
              <v-btn
                :icon="mdiPencil"
                variant="text"
                size="small"
                class="hs-table-icon-action"
                color="grey-darken-2"
                :disabled="!canEdit"
                :aria-label="`Edit ${serviceAccountItem.name}`"
                @click="openDialog(serviceAccountItem, 'edit')"
              />
              <v-btn
                :icon="mdiTrashCanOutline"
                variant="text"
                size="small"
                class="hs-table-icon-action hs-table-icon-action--danger"
                color="grey-darken-2"
                :disabled="!canDelete"
                :aria-label="`Delete ${serviceAccountItem.name}`"
                @click="openDialog(serviceAccountItem, 'delete')"
              />
            </td>
          </tr>
          <tr v-if="!filteredItems.length">
            <td colspan="2" class="text-center text-medium-emphasis">
              {{
                search || hasActiveFilters
                  ? 'No matching service accounts.'
                  : 'No service accounts available'
              }}
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </div>

  <v-dialog v-model="openCreate" width="40rem">
    <ServiceAccountForm
      @close="openCreate = false"
      @created="onCreate"
      :workspace-id="workspaceId"
      :roles="roles"
      :can-assign-role="canAssignRoleOnCreate"
    />
  </v-dialog>

  <v-dialog v-model="openRefresh" width="40rem">
    <ServiceAccountRegenerateForm
      @close="openRefresh = false"
      @regenerated="onRegenerate"
      :loading="isRegenerating"
    />
  </v-dialog>

  <v-dialog v-model="openEdit" width="40rem">
    <ServiceAccountForm
      @close="openEdit = false"
      @updated="onUpdate"
      :workspace-id="workspaceId"
      :roles="roles"
      :service-account="item"
      :can-assign-role="canAssignRoleOnEdit"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DeleteServiceAccount
      :itemName="item.name"
      :loading="isDeleting"
      @delete="onDelete"
      @close="openDelete = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import hs, {
  ServiceAccount,
  CollaboratorRole,
  PermissionAction,
  PermissionResource,
  Workspace,
} from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTableLogic } from '@/composables/useTableLogic'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import PermissionTooltip from '@/components/PermissionTooltip.vue'
import ServiceAccountForm from './ServiceAccountForm.vue'
import DeleteServiceAccount from './DeleteServiceAccount.vue'
import ServiceAccountRegenerateForm from './ServiceAccountRegenerateForm.vue'
import {
  mdiChevronDown,
  mdiContentCopy,
  mdiTrashCanOutline,
  mdiHelpCircleOutline,
  mdiMagnify,
  mdiPencil,
  mdiRefresh,
} from '@mdi/js'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['changed'])

const route = useRoute()
const router = useRouter()

const workspaceId = computed(() => props.workspace.id)
const { hasPermission } = useWorkspacePermissions()
const serviceAccountsLoaded = ref(false)
const rolesLoaded = ref(false)
const canAssignRoleOnCreate = computed(() =>
  hasPermission(
    PermissionResource.Collaborator,
    PermissionAction.Create,
    props.workspace
  )
)
const canAssignRoleOnEdit = computed(() =>
  hasPermission(
    PermissionResource.Collaborator,
    PermissionAction.Edit,
    props.workspace
  )
)
const canCreate = computed(
  () =>
    serviceAccountsLoaded.value &&
    rolesLoaded.value &&
    canAssignRoleOnCreate.value &&
    hasPermission(
      PermissionResource.ServiceAccount,
      PermissionAction.Create,
      props.workspace
    )
)
const canEdit = computed(
  () =>
    serviceAccountsLoaded.value &&
    hasPermission(
      PermissionResource.ServiceAccount,
      PermissionAction.Edit,
      props.workspace
    )
)
const canDelete = computed(
  () =>
    serviceAccountsLoaded.value &&
    hasPermission(
      PermissionResource.ServiceAccount,
      PermissionAction.Delete,
      props.workspace
    )
)

const openCreate = ref(false)
const openRefresh = ref(false)
const showServiceAccountHelp = ref(false)
const roles = ref<CollaboratorRole[]>([])
const roleFilterSearch = ref('')
const serviceAccountsLoadError = ref('')
const rolesLoadError = ref('')
const isLoading = ref(false)
const isDeleting = ref(false)
const isRegenerating = ref(false)
const loadError = computed(
  () => serviceAccountsLoadError.value || rolesLoadError.value
)

const showNewKey = ref(false)
type ServiceAccountRow = ServiceAccount & { role?: CollaboratorRole }

const newKey = ref<ServiceAccountRow>()

const {
  item,
  items,
  openEdit,
  openDelete,
  openDialog,
  onUpdate: updateTableItem,
  onDelete: deleteTableItem,
  loadData,
} = useTableLogic<ServiceAccountRow>(
  async (wsId: string) => {
    try {
      const [accountsRes, collaboratorsRes] = await Promise.all([
        hs.workspaces.getServiceAccounts(wsId),
        hs.workspaces.getCollaborators(wsId),
      ])
      if (!accountsRes.ok) {
        serviceAccountsLoadError.value = 'Unable to load service accounts.'
        serviceAccountsLoaded.value = false
        throw new Error(
          accountsRes.message || 'Unable to load service accounts.'
        )
      }

      const roleByEmail = new Map<string, CollaboratorRole>()
      if (collaboratorsRes.ok) {
        for (const collaborator of collaboratorsRes.data) {
          if (collaborator.serviceAccount)
            roleByEmail.set(
              collaborator.serviceAccount.email,
              collaborator.role
            )
        }
      }

      serviceAccountsLoadError.value = ''
      serviceAccountsLoaded.value = true
      return accountsRes.data
        .map((account) => ({
          ...account,
          role: roleByEmail.get(account.email),
        }))
        .sort((a, b) => a.name.localeCompare(b.name))
    } catch (error) {
      serviceAccountsLoadError.value = 'Unable to load service accounts.'
      serviceAccountsLoaded.value = false
      throw error
    }
  },
  async (serviceAccountId: string) => {
    const res = await hs.workspaces.deleteServiceAccount(
      workspaceId.value,
      serviceAccountId
    )
    if (!res.ok) {
      Snackbar.error(res.message || 'Failed to delete service account')
      throw new Error(res.message || 'Failed to delete service account')
    }
  },
  ServiceAccount,
  workspaceId
)

// The search bar is the single source of truth for filtering, following the
// GitHub issues search pattern (mirrors ManageCollaborators.vue): a typed
// qualifier like `role:Editor` drives both the role filter menu and the URL,
// so the whole filter state can be shared or bookmarked as a link.
const QUALIFIER_PATTERN = /(role):(?:"([^"]*)"|(\S+))/gi

function quoteIfNeeded(value: string) {
  return /\s/.test(value) ? `"${value}"` : value
}

function parseServiceAccountQuery(raw: string) {
  const roleValues: string[] = []
  const textParts: string[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  QUALIFIER_PATTERN.lastIndex = 0
  while ((match = QUALIFIER_PATTERN.exec(raw))) {
    textParts.push(raw.slice(lastIndex, match.index))
    const value = (match[2] ?? match[3] ?? '').trim()
    if (value) roleValues.push(value)
    lastIndex = QUALIFIER_PATTERN.lastIndex
  }
  textParts.push(raw.slice(lastIndex))
  return {
    roles: roleValues,
    text: textParts.join(' ').replace(/\s+/g, ' ').trim(),
  }
}

function serializeServiceAccountQuery(roleValues: string[], text: string) {
  return [
    ...roleValues.map((role) => `role:${quoteIfNeeded(role)}`),
    ...(text.trim() ? [text.trim()] : []),
  ].join(' ')
}

const search = ref('')
const parsedQuery = computed(() => parseServiceAccountQuery(search.value))
const selectedRoles = computed<string[]>({
  get: () => parsedQuery.value.roles,
  set: (value) =>
    (search.value = serializeServiceAccountQuery(value, parsedQuery.value.text)),
})

function toggleRole(role: string) {
  selectedRoles.value = selectedRoles.value.includes(role)
    ? selectedRoles.value.filter((r) => r !== role)
    : [...selectedRoles.value, role]
}

const hasActiveFilters = computed(() => selectedRoles.value.length > 0)
const availableRoles = computed(() =>
  [
    ...new Set(
      items.value.map((item) => item.role?.name).filter(Boolean) as string[]
    ),
  ].sort((a, b) => a.localeCompare(b))
)
const filteredRoles = computed(() => {
  const query = roleFilterSearch.value.trim().toLocaleLowerCase()
  return availableRoles.value.filter((role) =>
    role.toLocaleLowerCase().includes(query)
  )
})
const filteredItems = computed(() => {
  const { roles: roleValues, text } = parsedQuery.value
  const query = text.toLocaleLowerCase()
  return items.value.filter(
    (account) =>
      (!query ||
        [account.name, account.email, account.role?.name].some((value) =>
          String(value ?? '')
            .toLocaleLowerCase()
            .includes(query)
        )) &&
      (!roleValues.length ||
        roleValues.some(
          (role) =>
            role.toLocaleLowerCase() ===
            String(account.role?.name ?? '').toLocaleLowerCase()
        ))
  )
})

// Syntax highlighting: colors the value of a `role:value` pair primary when
// it matches a real role, the way GitHub highlights valid qualifier values.
function isValidQualifierValue(value: string) {
  return availableRoles.value.some(
    (role) => role.toLocaleLowerCase() === value.toLocaleLowerCase()
  )
}

const highlightSegments = computed(() => {
  const raw = search.value
  const segments: { text: string; cls: string }[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  QUALIFIER_PATTERN.lastIndex = 0
  while ((match = QUALIFIER_PATTERN.exec(raw))) {
    if (match.index > lastIndex)
      segments.push({ text: raw.slice(lastIndex, match.index), cls: '' })
    const quoted = match[2] !== undefined
    const value = match[2] ?? match[3] ?? ''
    segments.push({ text: match[1], cls: 'hl-key' })
    segments.push({ text: ':', cls: 'hl-colon' })
    segments.push({
      text: quoted ? `"${value}"` : value,
      cls: value && isValidQualifierValue(value) ? 'hl-value-valid' : '',
    })
    lastIndex = QUALIFIER_PATTERN.lastIndex
  }
  if (lastIndex < raw.length)
    segments.push({ text: raw.slice(lastIndex), cls: '' })
  return segments
})

// Autocomplete: suggests `role` while a qualifier key is being typed, and
// suggests the matching role values once followed by `:`, mirroring
// ManageCollaborators.vue's issue-search-style qualifier picker.
const QUALIFIER_KEYS = ['role'] as const

const searchInputEl = ref<HTMLInputElement | null>(null)
const caret = ref(0)
const suggestionIndex = ref(0)
const suggestionsEnabled = ref(false)
const suggestionStyle = computed(() => {
  const input = searchInputEl.value
  if (!input) return {}
  const rect = input.getBoundingClientRect()
  return {
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
  }
})

function syncCaret() {
  const el = searchInputEl.value
  if (el) caret.value = el.selectionStart ?? el.value.length
}

function onSearchInput() {
  syncCaret()
  suggestionsEnabled.value = true
}

function onSearchFocus() {
  suggestionsEnabled.value = true
  syncCaret()
}

function onSearchBlur() {
  suggestionsEnabled.value = false
}

// Finds where the qualifier token under the caret begins, treating a space
// inside an open quote as part of the value rather than a token boundary
// (so `role:"Data Manager |` still resolves to the `role` key).
function findTokenStart(raw: string, caretPos: number) {
  let inQuotes = false
  let tokenStart = 0
  for (let i = 0; i < caretPos; i++) {
    const char = raw[i]
    if (char === '"') inQuotes = !inQuotes
    else if (char === ' ' && !inQuotes) tokenStart = i + 1
  }
  return tokenStart
}

const currentToken = computed(() => {
  const raw = search.value
  const end = Math.min(caret.value, raw.length)
  const start = findTokenStart(raw, end)
  return { start, end, text: raw.slice(start, end) }
})

const activeSuggestion = computed(() => {
  if (!suggestionsEnabled.value) return null
  const { text, start, end } = currentToken.value
  if (!text) return null

  const colonIndex = text.indexOf(':')
  if (colonIndex === -1) {
    const query = text.toLocaleLowerCase()
    const items = QUALIFIER_KEYS.filter((key) => key.startsWith(query))
    return items.length
      ? { type: 'key' as const, items, start, end }
      : null
  }

  const key = text.slice(0, colonIndex).toLocaleLowerCase()
  if (key !== 'role') return null

  let valueQuery = text.slice(colonIndex + 1)
  if (valueQuery.startsWith('"')) valueQuery = valueQuery.slice(1)
  if (valueQuery.endsWith('"')) valueQuery = valueQuery.slice(0, -1)
  const query = valueQuery.toLocaleLowerCase()

  const items = availableRoles.value.filter(
    (value) =>
      !selectedRoles.value.includes(value) &&
      value.toLocaleLowerCase().includes(query)
  )
  return { type: 'value' as const, items, start, end }
})

watch(activeSuggestion, () => {
  suggestionIndex.value = 0
})

function replaceCurrentToken(replacement: string) {
  const { start, end } = currentToken.value
  const raw = search.value
  const nextCaret = start + replacement.length
  search.value = raw.slice(0, start) + replacement + raw.slice(end)
  nextTick(() => {
    const el = searchInputEl.value
    if (!el) return
    el.focus()
    el.setSelectionRange(nextCaret, nextCaret)
    caret.value = nextCaret
  })
}

function applySuggestion(item: string) {
  const suggestion = activeSuggestion.value
  if (!suggestion) return
  // replaceCurrentToken swaps out the whole token (e.g. the full "role:"
  // typed so far), so a value pick has to re-include the key prefix rather
  // than just the value.
  replaceCurrentToken(
    suggestion.type === 'key' ? `${item}:` : `role:${quoteIfNeeded(item)} `
  )
}

function onSearchKeydown(event: KeyboardEvent) {
  const suggestion = activeSuggestion.value
  if (!suggestion?.items.length) return
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    suggestionIndex.value =
      (suggestionIndex.value + 1) % suggestion.items.length
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    suggestionIndex.value =
      (suggestionIndex.value - 1 + suggestion.items.length) %
      suggestion.items.length
  } else if (event.key === 'Enter' || event.key === 'Tab') {
    event.preventDefault()
    applySuggestion(suggestion.items[suggestionIndex.value])
  } else if (event.key === 'Escape') {
    suggestionsEnabled.value = false
  }
}

const onUpdate = (account: ServiceAccountRow) => {
  updateTableItem(account)
  emits('changed')
}

const onDelete = async () => {
  if (isDeleting.value) return
  isDeleting.value = true
  try {
    if (await deleteTableItem()) {
      if (newKey.value?.id === item.value.id) {
        showNewKey.value = false
        newKey.value = undefined
      }
      emits('changed')
    }
  } finally {
    isDeleting.value = false
  }
}

const onCreate = (account: ServiceAccountRow) => {
  items.value.push(account)
  items.value.sort((a, b) => a.name.localeCompare(b.name))
  displayNewKey(account)
  emits('changed')
}

const displayNewKey = (account: ServiceAccountRow) => {
  newKey.value = account
  showNewKey.value = true
}

function onOpenRegenerateDialog(selectedItem: ServiceAccountRow) {
  if (!canEdit.value) return
  item.value = selectedItem
  openRefresh.value = true
}

const onRegenerate = async () => {
  if (isRegenerating.value) return
  isRegenerating.value = true
  try {
    const res = await hs.workspaces.regenerateServiceAccountKey(
      workspaceId.value,
      item.value.id
    )
    if (!res.ok) {
      Snackbar.error('Failed to refresh service account API key')
      return
    }
    const responseKey: ServiceAccountRow = {
      ...res.data,
      role: item.value.role,
    }
    const idx = items.value.findIndex((k) => k.id === responseKey.id)
    if (idx !== -1) {
      items.value.splice(idx, 1, responseKey)
    } else {
      items.value.push(responseKey)
    }
    displayNewKey(responseKey)
    openRefresh.value = false
    emits('changed')
  } catch (error) {
    Snackbar.error('Failed to refresh service account API key')
    console.error('Failed to refresh service account API key', error)
  } finally {
    isRegenerating.value = false
  }
}

async function copyKey(key: string) {
  try {
    await navigator.clipboard.writeText(key)
    Snackbar.success('Service account API key copied to clipboard')
  } catch {
    Snackbar.error('Failed to copy key')
  }
}

async function loadRoles() {
  try {
    const res = await hs.workspaces.getRoles({
      workspace_id: [workspaceId.value, 'null'],
      order_by: ['name'],
    })
    if (!res.ok) {
      rolesLoadError.value = 'Unable to load service account roles.'
      rolesLoaded.value = false
      return
    }
    roles.value = res.data
    rolesLoadError.value = ''
    rolesLoaded.value = true
  } catch (error) {
    console.error('Error fetching service account roles', error)
    rolesLoadError.value = 'Unable to load service account roles.'
    rolesLoaded.value = false
  }
}

async function reloadData() {
  isLoading.value = true
  await Promise.all([loadData(), loadRoles()])
  isLoading.value = false
}

// The `q` query param mirrors the search bar so the current filter/search
// state can be reloaded or shared as a link, mirroring
// ManageCollaborators.vue and GitHub's issue search.
function queryString(value: unknown) {
  return `${Array.isArray(value) ? (value[0] ?? '') : (value ?? '')}`
}

onMounted(() => {
  const queryValue = queryString(route.query.q)
  if (queryValue) search.value = queryValue
  loadRoles()
})

watch(search, (value) => {
  if (queryString(route.query.q) === value) return
  void router.replace({ query: { ...route.query, q: value || undefined } })
})
</script>

<style scoped>
.service-accounts-section {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
.service-accounts-help-text {
  color: var(--hs-text-secondary);
  line-height: 1.5;
  max-width: 640px;
  margin-bottom: 10px;
}
.workspace-table-search {
  position: relative;
  flex: 1;
  max-width: 560px;
}
.workspace-table-search-icon {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  color: var(--hs-input-border);
  pointer-events: none;
}
.workspace-table-search input.workspace-table-search-input {
  position: relative;
  width: 100%;
  height: 30px;
  border: 1px solid var(--hs-input-border);
  border-radius: var(--hs-radius-sm);
  padding-left: 30px;
  padding-right: var(--hs-space-10);
  outline: none;
  /* Transparent so the highlight overlay behind it (in DOM order, painted
     underneath) shows through — same characters, rendered in color so valid
     qualifier values can be highlighted like GitHub does. The overlay
     carries the actual surface fill. */
  background: transparent;
  color: transparent;
  caret-color: var(--hs-text-secondary);
}
.workspace-table-search input.workspace-table-search-input::placeholder {
  color: var(--hs-text-secondary);
  opacity: 1;
}
.workspace-table-search-input:focus {
  border-color: rgb(var(--v-theme-primary));
  /* Inset so the ring never gets clipped by an ancestor's overflow:hidden. */
  box-shadow: inset 0 0 0 1px rgb(var(--v-theme-primary));
}
.workspace-table-search-highlight {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  padding-left: 30px;
  padding-right: var(--hs-space-10);
  background: var(--hs-surface);
  border-radius: var(--hs-radius-sm);
  white-space: pre;
  overflow: hidden;
  pointer-events: none;
  color: var(--hs-text-secondary);
}
.workspace-table-search-highlight .hl-value-valid {
  color: rgb(var(--v-theme-primary));
  font-weight: var(--hs-font-weight-semibold);
}
.workspace-search-suggestions {
  position: fixed;
  z-index: 2000;
  min-width: 220px;
  max-width: 320px;
  max-height: 240px;
  overflow-y: auto;
  padding: var(--hs-space-8) 0;
  /* This panel is teleported outside the theme root, so keep an opaque
     fallback for environments where the HydroServer surface alias is not
     inherited by body-mounted content. */
  background-color: var(--hs-surface, #fff);
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-sm);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}
.workspace-search-suggestions-title {
  padding: var(--hs-space-4) var(--hs-space-16) var(--hs-space-8);
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-2xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.workspace-search-suggestion {
  display: block;
  width: 100%;
  padding: var(--hs-space-8) var(--hs-space-16);
  text-align: left;
  color: var(--hs-text-primary);
  background: none;
  border: none;
  cursor: pointer;
}
.workspace-search-suggestion:hover,
.workspace-search-suggestion--active {
  background-color: var(--hs-surface-muted, #eef4fa);
  color: var(--hs-text-primary, #1c1b1f);
}
.service-account-header-filters {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
}
.service-account-filter-button {
  min-width: auto;
  color: var(--hs-text-primary);
  text-transform: none;
}
.service-account-filter-button--active {
  color: rgb(var(--v-theme-primary));
}
.filter-count {
  min-width: 18px;
  margin-left: 2px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  font-size: var(--hs-font-2xs);
  line-height: 18px;
  text-align: center;
}
.service-account-filter-menu {
  min-width: 280px;
  max-height: 320px;
  overflow-y: auto;
  padding: var(--hs-space-8) 0;
}
.service-account-filter-title {
  padding: var(--hs-space-8) var(--hs-space-16);
  color: var(--hs-text-primary);
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-semibold);
}
.service-account-filter-search {
  margin: 0 var(--hs-space-12) var(--hs-space-8);
  height: 30px;
}
.service-account-filter-search :deep(.v-field) {
  height: 30px;
  min-height: 30px;
  border-radius: var(--hs-radius-sm);
  background: var(--hs-surface);
  padding-inline-start: 0;
}
.service-account-filter-search :deep(.v-field__outline) {
  color: var(--hs-input-border);
  --v-field-border-opacity: 1;
}
.service-account-filter-search :deep(.v-field--focused) {
  box-shadow: none;
}
.service-account-filter-search :deep(.v-field--focused .v-field__outline) {
  color: rgb(var(--v-theme-primary));
  --v-field-border-width: 2px;
  --v-field-border-opacity: 1;
}
.service-account-filter-search :deep(.v-field__input) {
  min-height: 30px;
  padding-top: 0;
  padding-bottom: 0;
  font-size: var(--hs-font-sm);
}
.service-account-filter-search :deep(.v-field__prepend-inner) {
  padding-left: 8px;
  padding-right: 0;
}
.service-account-filter-search :deep(.v-field__prepend-inner > .v-icon) {
  width: 16px;
  font-size: var(--hs-font-md);
  color: var(--hs-input-border);
  opacity: 1;
}
.service-account-filter-search :deep(.v-field__append-inner) {
  padding-right: 8px;
}
.service-account-filter-search :deep(input::placeholder) {
  color: var(--hs-text-secondary);
  opacity: 1;
}
.filter-empty {
  padding: var(--hs-space-12) var(--hs-space-16);
  color: var(--hs-text-secondary);
}
.filter-clear-item {
  border-top: 1px solid var(--hs-border);
  color: rgb(var(--v-theme-primary));
}
.service-accounts-table-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  margin-top: 0;
  overflow: hidden;
}
.service-accounts-table {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.service-accounts-table :deep(td) {
  vertical-align: middle;
  padding-top: var(--hs-space-12);
  padding-bottom: var(--hs-space-12);
}
</style>
