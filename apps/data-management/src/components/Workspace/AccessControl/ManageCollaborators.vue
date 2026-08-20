<template>
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
      <v-btn variant="text" size="small" @click="loadCollaboratorData">
        Retry
      </v-btn>
    </div>
  </v-alert>
  <v-progress-linear v-if="isLoading" indeterminate class="mb-2" />

  <v-card
    v-if="showAddCollaborator"
    class="collaborator-add-card mb-4"
    variant="outlined"
  >
    <v-card-text>
      <v-text-field
        v-model="newCollaboratorEmail"
        label="New collaborator's email"
        data-testid="new-collaborator-email"
      />
      <v-select
        v-model="selectedRole"
        :items="roles"
        label="New collaborator's role"
        item-title="name"
        :return-object="true"
        variant="outlined"
        data-testid="new-collaborator-role"
      />
    </v-card-text>
    <v-divider />
    <v-card-actions>
      <v-spacer />
      <v-btn-cancel @click="cancelAddCollaborator">Cancel</v-btn-cancel>
      <v-btn-primary
        data-testid="submit-collaborator-button"
        :loading="isAdding"
        :disabled="isAdding"
        @click="onAddCollaborator"
      >
        Add collaborator
      </v-btn-primary>
    </v-card-actions>
  </v-card>

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
        placeholder="Search collaborators…"
        class="workspace-table-search-input hs-text-sm"
        aria-label="Search collaborators"
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
      title="About collaborators"
      aria-label="Toggle collaborator help"
      :aria-expanded="showAddCollaboratorHelp"
      @click="showAddCollaboratorHelp = !showAddCollaboratorHelp"
    />

    <div class="hs-table-actions">
      <PermissionTooltip
        :has-permission="canCreate"
        message="You don't have permission to add collaborators to this workspace."
      >
        <template #default>
          <v-btn-secondary
            variant="flat"
            data-testid="add-collaborator-button"
            @click="showAddCollaborator = true"
            >Add collaborator</v-btn-secondary
          >
        </template>

        <template #denied>
          <v-btn-primary
            variant="flat"
            disabled
            data-testid="add-collaborator-button"
            @click="showAddCollaborator = true"
            >Add collaborator</v-btn-primary
          >
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
        {{
          activeSuggestion.type === 'key'
            ? 'Filter by…'
            : `${activeSuggestion.key === 'role' ? 'Role' : 'Organization'} values`
        }}
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

  <p v-if="showAddCollaboratorHelp" class="collaborators-help-text">
    <small>
      You can add collaborators to this workspace with either Editor or Viewer
      roles. Viewers can see everything in the workspace but cannot edit.
      Editors can create, read, update, and delete all sites, metadata, and
      datastreams as well as set their visibility. Users can remove themselves
      as collaborators.
    </small>
  </p>

  <v-card class="hs-table-card collaborators-table-card" flat>
    <v-table class="collaborator-table">
      <thead>
        <tr>
          <th>
            <div class="collaborator-header-filters">
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
                    class="collaborator-filter-button"
                    :class="{
                      'collaborator-filter-button--active':
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
                <v-list class="collaborator-filter-menu" density="compact">
                  <div class="collaborator-filter-title">Filter by role</div>
                  <v-text-field
                    v-model="roleFilterSearch"
                    class="collaborator-filter-search"
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
                    class="collaborator-filter-button"
                    :class="{
                      'collaborator-filter-button--active':
                        selectedOrganizations.length,
                    }"
                    :append-icon="mdiChevronDown"
                    :aria-label="`Filter by organization${selectedOrganizations.length ? ` (${selectedOrganizations.length} selected)` : ''}`"
                  >
                    Organization
                    <span
                      v-if="selectedOrganizations.length"
                      class="filter-count"
                    >
                      {{ selectedOrganizations.length }}
                    </span>
                  </v-btn>
                </template>
                <v-list class="collaborator-filter-menu" density="compact">
                  <div class="collaborator-filter-title">
                    Filter by organization
                  </div>
                  <v-text-field
                    v-model="organizationFilterSearch"
                    class="collaborator-filter-search"
                    placeholder="Filter organizations"
                    :prepend-inner-icon="mdiMagnify"
                    variant="outlined"
                    density="compact"
                    hide-details
                    clearable
                  />
                  <v-list-item
                    v-for="organization in filteredOrganizations"
                    :key="organization"
                    @click="toggleOrganization(organization)"
                  >
                    <template #prepend>
                      <v-checkbox
                        :model-value="
                          selectedOrganizations.includes(organization)
                        "
                        hide-details
                        density="compact"
                        :aria-label="`Organization: ${organization}`"
                        @click.stop="toggleOrganization(organization)"
                      />
                    </template>
                    <v-list-item-title>{{ organization }}</v-list-item-title>
                  </v-list-item>
                  <v-list-item
                    v-if="selectedOrganizations.length"
                    class="filter-clear-item"
                    @click="selectedOrganizations = []"
                  >
                    <v-list-item-title>Clear filter</v-list-item-title>
                  </v-list-item>
                  <div
                    v-if="!filteredOrganizations.length"
                    class="filter-empty"
                  >
                    No organizations found
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
          v-for="item in filteredCollaborators"
          :key="item.email"
          :data-testid="`collaborator-row-${item.email}`"
        >
          <td>
            <div class="collaborator-name font-weight-medium">
              {{ item.name }}
            </div>
            <div class="hs-text-sm text-medium-emphasis">
              <span v-if="!item.isBeingEdited">
                {{ item.role.name }} · {{ item.email }} ·
                {{ item.organization }}
              </span>
              <v-select
                v-else
                v-model="item.pendingRole"
                :items="roles"
                item-title="name"
                :return-object="true"
                variant="outlined"
                density="compact"
                hide-details
                class="collaborator-role-editor"
              />
            </div>
          </td>
          <td class="text-right">
            <template v-if="item.isBeingEdited">
              <v-btn-cancel
                size="small"
                class="mr-2"
                @click="onCancelEdit(item)"
                >Cancel</v-btn-cancel
              >
              <v-btn
                size="small"
                :loading="item.isSaving"
                :disabled="item.isSaving"
                :data-testid="`save-collaborator-${item.email}`"
                @click="onSaveRole(item)"
                >Save</v-btn
              >
            </template>
            <template v-else>
              <PermissionTooltip
                :has-permission="canEditCollaborator(item)"
                :message="collaboratorEditDeniedMessage(item)"
              >
                <template #default>
                  <v-btn
                    variant="text"
                    size="small"
                    class="hs-table-icon-action"
                    color="grey-darken-2"
                    :icon="mdiPencil"
                    :data-testid="`edit-collaborator-${item.email}`"
                    :aria-label="`Edit ${item.name}`"
                    @click="item.isBeingEdited = true"
                  />
                </template>
                <template #denied>
                  <v-btn
                    variant="text"
                    size="small"
                    class="hs-table-icon-action"
                    color="grey-darken-2"
                    :icon="mdiPencilOffOutline"
                    disabled
                    :aria-label="`Edit ${item.name} unavailable`"
                  />
                </template>
              </PermissionTooltip>
              <PermissionTooltip
                :has-permission="canRemoveCollaborator(item)"
                :message="collaboratorRemoveDeniedMessage(item)"
              >
                <template #default>
                  <v-btn
                    variant="text"
                    size="small"
                    class="hs-table-icon-action hs-table-icon-action--danger"
                    color="grey-darken-2"
                    :icon="mdiTrashCanOutline"
                    :loading="removingEmail === item.email"
                    :disabled="!!removingEmail"
                    :data-testid="`remove-collaborator-${item.email}`"
                    :aria-label="`Remove ${item.name}`"
                    @click="onRemoveCollaborator(item.email)"
                  />
                </template>
                <template #denied>
                  <v-btn
                    variant="text"
                    size="small"
                    class="hs-table-icon-action hs-table-icon-action--danger"
                    color="grey-darken-2"
                    :icon="mdiDeleteOffOutline"
                    disabled
                    :aria-label="`Remove ${item.name} unavailable`"
                  />
                </template>
              </PermissionTooltip>
            </template>
          </td>
        </tr>
        <tr v-if="!filteredCollaborators.length">
          <td colspan="2" class="text-center text-medium-emphasis">
            {{
              search || hasActiveFilters
                ? 'No matching collaborators.'
                : 'No collaborators yet.'
            }}
          </td>
        </tr>
      </tbody>
    </v-table>
  </v-card>
</template>

<script setup lang="ts">
import { useUserStore } from '@/store/user'
import { Snackbar } from '@/utils/notifications'
import { storeToRefs } from 'pinia'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import hs, {
  PermissionAction,
  PermissionResource,
  Collaborator,
  CollaboratorRole,
  Workspace,
} from '@hydroserver/client'
import {
  mdiChevronDown,
  mdiDeleteOffOutline,
  mdiHelpCircleOutline,
  mdiMagnify,
  mdiPencil,
  mdiPencilOffOutline,
  mdiTrashCanOutline,
} from '@mdi/js'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import PermissionTooltip from '@/components/PermissionTooltip.vue'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
})
const emits = defineEmits(['self-removed', 'changed'])

const route = useRoute()
const router = useRouter()

const { user } = storeToRefs(useUserStore())
const { hasPermission } = useWorkspacePermissions()
const isDataReady = ref(false)
const canCreate = computed(
  () =>
    isDataReady.value &&
    hasPermission(
      PermissionResource.Collaborator,
      PermissionAction.Create,
      props.workspace
    )
)
const canEdit = computed(
  () =>
    isDataReady.value &&
    hasPermission(
      PermissionResource.Collaborator,
      PermissionAction.Edit,
      props.workspace
    )
)
const canDelete = computed(() =>
  hasPermission(
    PermissionResource.Collaborator,
    PermissionAction.Delete,
    props.workspace
  )
)
const canRemove = (item: { email: string }) =>
  canDelete.value || item.email === user.value?.email
const canEditCollaborator = (item: { isOwner?: boolean }) =>
  canEdit.value && !item.isOwner
const canRemoveCollaborator = (item: { email: string; isOwner?: boolean }) =>
  canRemove(item) && !item.isOwner
const collaboratorEditDeniedMessage = (item: { isOwner?: boolean }) =>
  item.isOwner
    ? 'The workspace owner cannot be edited.'
    : "You don't have permission to edit collaborators."
const collaboratorRemoveDeniedMessage = (item: {
  email: string
  isOwner?: boolean
}) =>
  item.isOwner
    ? 'The workspace owner cannot be removed.'
    : "You don't have permission to remove collaborators."

const showAddCollaboratorHelp = ref(false)
const showAddCollaborator = ref(false)
const selectedRole = ref()
const newCollaboratorEmail = ref('')
const roles = ref<CollaboratorRole[]>([])
const collaboratorList = ref<any[]>([])
const roleFilterSearch = ref('')
const organizationFilterSearch = ref('')

// The search bar is the single source of truth for filtering, following the
// GitHub issues search pattern: typed qualifiers like `role:Editor` and
// `organization:"Utah State University"` drive both the filter menus and the
// URL, so the whole filter state can be shared or bookmarked as a link.
const QUALIFIER_PATTERN = /(role|organization):(?:"([^"]*)"|(\S+))/gi

function quoteIfNeeded(value: string) {
  return /\s/.test(value) ? `"${value}"` : value
}

function parseCollaboratorQuery(raw: string) {
  const roleValues: string[] = []
  const organizationValues: string[] = []
  const textParts: string[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  QUALIFIER_PATTERN.lastIndex = 0
  while ((match = QUALIFIER_PATTERN.exec(raw))) {
    textParts.push(raw.slice(lastIndex, match.index))
    const key = match[1].toLocaleLowerCase()
    const value = (match[2] ?? match[3] ?? '').trim()
    if (value) (key === 'role' ? roleValues : organizationValues).push(value)
    lastIndex = QUALIFIER_PATTERN.lastIndex
  }
  textParts.push(raw.slice(lastIndex))
  return {
    roles: roleValues,
    organizations: organizationValues,
    text: textParts.join(' ').replace(/\s+/g, ' ').trim(),
  }
}

function serializeCollaboratorQuery(
  roleValues: string[],
  organizationValues: string[],
  text: string
) {
  return [
    ...roleValues.map((role) => `role:${quoteIfNeeded(role)}`),
    ...organizationValues.map(
      (organization) => `organization:${quoteIfNeeded(organization)}`
    ),
    ...(text.trim() ? [text.trim()] : []),
  ].join(' ')
}

const search = ref('')
const parsedQuery = computed(() => parseCollaboratorQuery(search.value))
const selectedRoles = computed<string[]>({
  get: () => parsedQuery.value.roles,
  set: (value) =>
    (search.value = serializeCollaboratorQuery(
      value,
      parsedQuery.value.organizations,
      parsedQuery.value.text
    )),
})
const selectedOrganizations = computed<string[]>({
  get: () => parsedQuery.value.organizations,
  set: (value) =>
    (search.value = serializeCollaboratorQuery(
      parsedQuery.value.roles,
      value,
      parsedQuery.value.text
    )),
})

function toggleRole(role: string) {
  selectedRoles.value = selectedRoles.value.includes(role)
    ? selectedRoles.value.filter((r) => r !== role)
    : [...selectedRoles.value, role]
}

function toggleOrganization(organization: string) {
  selectedOrganizations.value = selectedOrganizations.value.includes(
    organization
  )
    ? selectedOrganizations.value.filter((o) => o !== organization)
    : [...selectedOrganizations.value, organization]
}

const hasActiveFilters = computed(
  () => selectedRoles.value.length > 0 || selectedOrganizations.value.length > 0
)
const availableRoles = computed(() =>
  [
    ...new Set(
      collaboratorList.value.map((item) => item.role?.name).filter(Boolean)
    ),
  ].sort((a, b) => a.localeCompare(b))
)
const availableOrganizations = computed(() =>
  [
    ...new Set(
      collaboratorList.value.map((item) => item.organization).filter(Boolean)
    ),
  ].sort((a, b) => a.localeCompare(b))
)
const filteredRoles = computed(() => {
  const query = roleFilterSearch.value.trim().toLocaleLowerCase()
  return availableRoles.value.filter((role) =>
    role.toLocaleLowerCase().includes(query)
  )
})
const filteredOrganizations = computed(() => {
  const query = organizationFilterSearch.value.trim().toLocaleLowerCase()
  return availableOrganizations.value.filter((organization) =>
    organization.toLocaleLowerCase().includes(query)
  )
})
const filteredCollaborators = computed(() => {
  const {
    roles: roleValues,
    organizations: organizationValues,
    text,
  } = parsedQuery.value
  const query = text.toLocaleLowerCase()
  return collaboratorList.value.filter(
    (collaborator) =>
      (!query ||
        [
          collaborator.name,
          collaborator.email,
          collaborator.organization,
          collaborator.role?.name,
        ].some((value) =>
          String(value ?? '')
            .toLocaleLowerCase()
            .includes(query)
        )) &&
      (!roleValues.length ||
        roleValues.some(
          (role) =>
            role.toLocaleLowerCase() ===
            String(collaborator.role?.name ?? '').toLocaleLowerCase()
        )) &&
      (!organizationValues.length ||
        organizationValues.some(
          (organization) =>
            organization.toLocaleLowerCase() ===
            String(collaborator.organization ?? '').toLocaleLowerCase()
        ))
  )
})
// Syntax highlighting: colors the value of a `key:value` pair primary when
// it matches a real role/organization, the way GitHub highlights valid
// qualifier values in its issue search bar.
function isValidQualifierValue(key: string, value: string) {
  const pool =
    key === 'role' ? availableRoles.value : availableOrganizations.value
  return pool.some(
    (item) => item.toLocaleLowerCase() === value.toLocaleLowerCase()
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
    const key = match[1].toLocaleLowerCase()
    const quoted = match[2] !== undefined
    const value = match[2] ?? match[3] ?? ''
    segments.push({ text: match[1], cls: 'hl-key' })
    segments.push({ text: ':', cls: 'hl-colon' })
    segments.push({
      text: quoted ? `"${value}"` : value,
      cls: value && isValidQualifierValue(key, value) ? 'hl-value-valid' : '',
    })
    lastIndex = QUALIFIER_PATTERN.lastIndex
  }
  if (lastIndex < raw.length)
    segments.push({ text: raw.slice(lastIndex), cls: '' })
  return segments
})

// Autocomplete: suggests `role`/`organization` while a qualifier key is being
// typed, and suggests the matching values once a key is followed by `:`,
// mirroring GitHub's issue search qualifier picker.
const QUALIFIER_KEYS = ['role', 'organization'] as const

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
// (so `organization:"Utah State |` still resolves to the `organization` key).
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
      ? { type: 'key' as const, key: null, items, start, end }
      : null
  }

  const key = text.slice(0, colonIndex).toLocaleLowerCase()
  if (key !== 'role' && key !== 'organization') return null

  let valueQuery = text.slice(colonIndex + 1)
  if (valueQuery.startsWith('"')) valueQuery = valueQuery.slice(1)
  if (valueQuery.endsWith('"')) valueQuery = valueQuery.slice(0, -1)
  const query = valueQuery.toLocaleLowerCase()

  const pool =
    key === 'role' ? availableRoles.value : availableOrganizations.value
  const selected =
    key === 'role' ? selectedRoles.value : selectedOrganizations.value
  const items = pool.filter(
    (value) =>
      !selected.includes(value) && value.toLocaleLowerCase().includes(query)
  )
  return { type: 'value' as const, key, items, start, end }
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
    suggestion.type === 'key'
      ? `${item}:`
      : `${suggestion.key}:${quoteIfNeeded(item)} `
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

const isLoading = ref(false)
const loadError = ref('')
const isAdding = ref(false)
const removingEmail = ref('')

/**
 * Save the new role, then reset editing state
 */
async function onSaveRole(item: any) {
  if (!canEdit.value || item.isSaving) return
  item.isSaving = true
  try {
    const res = await hs.workspaces.updateCollaboratorRole(
      props.workspace.id,
      item.email,
      item.pendingRole.id
    )
    if (res.ok) {
      item.role = res.data.role
      item.isBeingEdited = false
      Snackbar.success('Collaborator role updated.')
      emits('changed')
    } else {
      console.error('Error updating collaborator role:', res)
      Snackbar.error(res.message || 'Unable to update the collaborator role.')
      item.isBeingEdited = true
    }
  } catch (error) {
    console.error('Error updating collaborator role:', error)
    Snackbar.error('Unable to update the collaborator role.')
  } finally {
    item.isSaving = false
  }
}

function cancelAddCollaborator() {
  showAddCollaborator.value = false
  selectedRole.value = ''
  newCollaboratorEmail.value = ''
}

async function onAddCollaborator() {
  if (!canCreate.value || isAdding.value) return
  if (!newCollaboratorEmail.value || !selectedRole.value) {
    Snackbar.warn('Please fill out collaborator email and role.')
    return
  }

  isAdding.value = true
  try {
    const res = await hs.workspaces.addCollaborator(
      props.workspace!.id,
      newCollaboratorEmail.value,
      selectedRole.value.id
    )
    if (res.ok) {
      if (res.data.user && !res.data.serviceAccount) {
        collaboratorList.value.push(collaboratorToFormData(res.data))
      }
      collaboratorList.value.sort((a, b) => a.name.localeCompare(b.name))
      Snackbar.success('Collaborator added to workspace.')
      showAddCollaborator.value = false
      newCollaboratorEmail.value = ''
      selectedRole.value = ''
      emits('changed')
    } else {
      console.error('Error adding collaborator', res)
      Snackbar.error(res.message || 'Unable to add the collaborator.')
    }
  } catch (error) {
    console.error('Error adding collaborator', error)
    Snackbar.error('Unable to add the collaborator.')
  } finally {
    isAdding.value = false
  }
}

async function onRemoveCollaborator(email: string) {
  if (removingEmail.value || (!canDelete.value && email !== user.value?.email))
    return
  removingEmail.value = email
  try {
    const res = await hs.workspaces.removeCollaborator(
      props.workspace!.id,
      email
    )

    if (res.ok) {
      const index = collaboratorList.value.findIndex((c) => c.email === email)
      if (index !== -1) collaboratorList.value.splice(index, 1)
      Snackbar.success('Collaborator removed.')
      emits('changed')
      if (email === user.value.email) emits('self-removed')
    } else {
      console.error('Error removing collaborator', res)
      Snackbar.error(res.message || 'Unable to remove the collaborator.')
    }
  } catch (error) {
    console.error('Error removing collaborator', error)
    Snackbar.error('Unable to remove the collaborator.')
  } finally {
    removingEmail.value = ''
  }
}

const setCollaboratorList = (collaborators: Collaborator[]) => {
  collaboratorList.value = collaborators
    .filter((collaborator) => collaborator.user && !collaborator.serviceAccount)
    .map((collaborator) => collaboratorToFormData(collaborator))

  if (props.workspace?.owner) {
    collaboratorList.value.unshift({
      email: props.workspace.owner.email,
      value: props.workspace.owner.email,
      name: props.workspace.owner.name,
      role: { name: 'Owner' },
      organization: props.workspace.owner.organizationName || 'No Organization',
      isOwner: true,
      isBeingEdited: false,
      isSaving: false,
    })
  }
  collaboratorList.value.sort((a, b) => a.name.localeCompare(b.name))
}

async function onCancelEdit(item: any) {
  item.pendingRole = item.role
  item.isBeingEdited = false
}

const collaboratorToFormData = (c: Collaborator) => {
  const contact = c.user
  return {
    email: contact?.email ?? '',
    value: contact?.email ?? '',
    name: contact?.name ?? '',
    role: c.role,
    pendingRole: c.role,
    organization: c.user?.organizationName || 'No Organization',
    isOwner: false,
    isBeingEdited: false,
    isSaving: false,
  }
}

async function loadCollaboratorData() {
  isLoading.value = true
  loadError.value = ''
  isDataReady.value = false
  try {
    const [cRes, rolesResponse] = await Promise.all([
      hs.workspaces.getCollaborators(props.workspace.id),
      hs.workspaces.getRoles({
        order_by: ['name'],
      }),
    ])

    if (!cRes.ok || !rolesResponse.ok) {
      console.error('Error fetching workspace collaborators', {
        collaborators: cRes,
        roles: rolesResponse,
      })
      loadError.value = 'Unable to load all collaborator data.'
    }

    roles.value = rolesResponse.ok
      ? rolesResponse.data.filter(
          (role: CollaboratorRole) =>
            role.workspaceId === null || role.workspaceId === props.workspace.id
        )
      : []
    setCollaboratorList(cRes.ok ? cRes.data : [])
    isDataReady.value = cRes.ok && rolesResponse.ok
  } catch (error) {
    console.error('Error fetching workspace collaborators', error)
    loadError.value = 'Unable to load collaborator data.'
    roles.value = []
    setCollaboratorList([])
  } finally {
    isLoading.value = false
  }
}

// The `q` query param mirrors the search bar so the current filter/search
// state can be reloaded or shared as a link, mirroring GitHub's issue search.
function queryString(value: unknown) {
  return `${Array.isArray(value) ? (value[0] ?? '') : (value ?? '')}`
}

onMounted(() => {
  const queryValue = queryString(route.query.q)
  if (queryValue) search.value = queryValue
  loadCollaboratorData()
})

watch(search, (value) => {
  if (queryString(route.query.q) === value) return
  void router.replace({ query: { ...route.query, q: value || undefined } })
})
</script>

<style scoped>
.collaborator-add-card {
  background-color: var(--hs-surface) !important;
  border-color: var(--hs-border) !important;
  opacity: 1;
}

.collaborator-add-card :deep(.v-field) {
  background-color: var(--hs-surface-subtle);
}

.collaborators-help-text {
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
.collaborator-filter-button {
  min-width: auto;
  color: var(--hs-text-primary);
  text-transform: none;
}
.collaborator-filter-button--active {
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
.collaborator-filter-menu {
  min-width: 280px;
  max-height: 320px;
  overflow-y: auto;
  padding: var(--hs-space-8) 0;
}
.collaborator-filter-title {
  padding: var(--hs-space-8) var(--hs-space-16);
  color: var(--hs-text-primary);
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-semibold);
}
.collaborator-filter-search {
  margin: 0 var(--hs-space-12) var(--hs-space-8);
  height: 30px;
}
.collaborator-filter-search :deep(.v-field) {
  height: 30px;
  min-height: 30px;
  border-radius: var(--hs-radius-sm);
  background: var(--hs-surface);
  padding-inline-start: 0;
}
.collaborator-filter-search :deep(.v-field__outline) {
  color: var(--hs-input-border);
  --v-field-border-opacity: 1;
}
.collaborator-filter-search :deep(.v-field--focused) {
  box-shadow: none;
}
.collaborator-filter-search :deep(.v-field--focused .v-field__outline) {
  color: rgb(var(--v-theme-primary));
  --v-field-border-width: 2px;
  --v-field-border-opacity: 1;
}
.collaborator-filter-search :deep(.v-field__input) {
  min-height: 30px;
  padding-top: 0;
  padding-bottom: 0;
  font-size: var(--hs-font-sm);
}
.collaborator-filter-search :deep(.v-field__prepend-inner) {
  padding-left: 8px;
  padding-right: 0;
}
.collaborator-filter-search :deep(.v-field__prepend-inner > .v-icon) {
  width: 16px;
  font-size: var(--hs-font-md);
  color: var(--hs-input-border);
  opacity: 1;
}
.collaborator-filter-search :deep(.v-field__append-inner) {
  padding-right: 8px;
}
.collaborator-filter-search :deep(input::placeholder) {
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
.collaborator-role-editor {
  max-width: 200px;
  margin-top: 4px;
}
.workspace-table-search-input:focus {
  border-color: rgb(var(--v-theme-primary));
  /* Inset so the ring never gets clipped by an ancestor's overflow:hidden
     (the search bar sits flush against the tab-window's left edge). */
  box-shadow: inset 0 0 0 1px rgb(var(--v-theme-primary));
}
.collaborators-table-card {
  margin-top: 0;
}
.collaborator-header-filters {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
}
.collaborator-table :deep(td) {
  vertical-align: middle;
  padding-top: var(--hs-space-12);
  padding-bottom: var(--hs-space-12);
}
</style>
