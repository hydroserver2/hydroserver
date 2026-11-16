<template>
  <v-menu
    v-model="open"
    :close-on-content-click="false"
    location="bottom start"
    attach="body"
    @after-enter="resetScroll"
  >
    <template #activator="slotProps">
      <slot name="activator" v-bind="slotProps" />
    </template>

    <v-card class="hs-table-filter-menu" :aria-label="title">
      <header class="hs-table-filter-menu__header">
        <h3 class="hs-title">{{ title }}</h3>
        <HsSearchInput
          v-if="searchable"
          v-model="search"
          :placeholder="searchPlaceholder || `Filter ${label.toLowerCase()}`"
        />
      </header>

      <v-list
        ref="optionList"
        class="hs-table-filter-menu__options"
        density="compact"
      >
        <template v-for="group in groups" :key="group.id">
          <v-divider
            v-if="group.id === 'available' && selectedOptions.length"
          />
          <div
            :aria-label="
              group.id === 'selected' ? selectedHeading : sectionHeading
            "
            role="group"
            :class="`hs-table-filter-menu__${group.id}`"
          >
            <div
              v-if="selectedOptions.length"
              class="hs-table-filter-menu__section-title hs-label"
            >
              {{ group.id === 'selected' ? selectedHeading : sectionHeading }}
            </div>
            <v-list-item
              v-for="option in group.options"
              :key="option.value"
              class="hs-table-filter-menu__option"
              :ripple="false"
              :role="showCheckboxes ? undefined : 'menuitemcheckbox'"
              :aria-checked="
                showCheckboxes ? undefined : isSelected(option.value)
              "
              @click="emit('toggle', option.value)"
            >
              <template #prepend>
                <v-checkbox-btn
                  v-if="showCheckboxes"
                  :model-value="isSelected(option.value)"
                  density="compact"
                  :aria-label="`${label}: ${option.label}`"
                  @click.stop="emit('toggle', option.value)"
                />
                <v-icon
                  v-else
                  :icon="mdiCheck"
                  size="18"
                  :class="{
                    'hs-table-filter-menu__check--hidden': !isSelected(
                      option.value
                    ),
                  }"
                />
              </template>
              <v-list-item-title
                class="hs-table-filter-menu__option-label hs-text-sm"
              >
                <v-icon
                  v-if="option.icon"
                  :icon="option.icon"
                  size="18"
                  :style="{ color: option.color }"
                />
                <span>{{ option.label }}</span>
              </v-list-item-title>
            </v-list-item>
            <div
              v-if="group.id === 'available' && !group.options.length"
              class="hs-table-filter-menu__empty hs-text-sm"
            >
              {{
                !search.trim() && selectedOptions.length
                  ? 'No other options'
                  : emptyText
              }}
            </div>
          </div>
        </template>
      </v-list>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { mdiCheck } from '@mdi/js'
import HsSearchInput from './HsSearchInput.vue'
import type { HsTableFilterOption } from './types'

defineOptions({ name: 'HsTableFilterMenu' })

const props = withDefaults(
  defineProps<{
    title: string
    label: string
    sectionLabel?: string
    options: readonly HsTableFilterOption[]
    selected: readonly string[]
    searchable?: boolean
    searchPlaceholder?: string
    emptyText?: string
    showCheckboxes?: boolean
    caseInsensitive?: boolean
  }>(),
  {
    searchable: true,
    sectionLabel: '',
    searchPlaceholder: '',
    emptyText: 'No options found',
    showCheckboxes: true,
    caseInsensitive: false,
  }
)

const emit = defineEmits<{ toggle: [value: string] }>()
const search = defineModel<string>('search', { default: '' })
const open = ref(false)
const sectionHeading = computed(() => props.sectionLabel || props.label)
const selectedHeading = computed(
  () => `Selected ${sectionHeading.value.toLocaleLowerCase()}`
)
const optionList = ref<{ $el: HTMLElement }>()
const normalize = (value: string) =>
  props.caseInsensitive ? value.toLocaleLowerCase() : value
const selectedValues = computed(() => new Set(props.selected.map(normalize)))
const isSelected = (value: string) => selectedValues.value.has(normalize(value))
const sessionOptions = ref(props.options.map((option) => ({ ...option })))
const sessionSelected = ref([...props.selected])
watch(
  () => props.options,
  (options) => {
    // Options can arrive after the menu is opened while its table loads.
    // Once populated, keep the opening snapshot stable until reopening.
    if (open.value && !sessionOptions.value.length && options.length) {
      sessionOptions.value = options.map((option) => ({ ...option }))
    }
  }
)
const selectedOptions = computed<HsTableFilterOption[]>(() => {
  const byValue = new Map(
    sessionOptions.value.map((option) => [normalize(option.value), option])
  )
  // Keep selections available to remove even when another filter excludes
  // their options, or the current search doesn't match their labels.
  return sessionSelected.value.map((value) => ({
    ...(byValue.get(normalize(value)) ?? { label: value }),
    value,
  }))
})
const availableOptions = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  const selectedAtOpen = new Set(sessionSelected.value.map(normalize))
  return sessionOptions.value.filter(
    (option) =>
      !selectedAtOpen.has(normalize(option.value)) &&
      (!query || option.label.toLocaleLowerCase().includes(query))
  )
})
const groups = computed(() => [
  { id: 'selected', options: selectedOptions.value },
  { id: 'available', options: availableOptions.value },
])

function resetScroll() {
  if (optionList.value) optionList.value.$el.scrollTop = 0
}

watch(open, async (isOpen) => {
  if (!isOpen) return
  // Apply checkbox changes immediately, but only regroup when reopening so
  // options don't jump away from the pointer or keyboard focus mid-selection.
  sessionOptions.value = props.options.map((option) => ({ ...option }))
  sessionSelected.value = [...props.selected]
  await nextTick()
  resetScroll()
})
</script>

<style scoped>
.hs-table-filter-menu {
  display: flex;
  flex-direction: column;
  width: min(360px, calc(100vw - var(--hs-space-32)));
  max-height: min(320px, calc(100dvh - var(--hs-space-32)));
  overflow: hidden;
  background: var(--hs-surface);
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-md);
}
.hs-table-filter-menu__header {
  display: flex;
  flex: none;
  flex-direction: column;
  gap: var(--hs-space-8);
  padding: var(--hs-space-12);
  border-bottom: 1px solid var(--hs-border);
}
.hs-table-filter-menu__header h3 {
  margin: 0;
  color: var(--hs-text-primary);
}
.hs-table-filter-menu__options {
  flex: 1 1 auto;
  min-height: 0;
  padding: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.hs-table-filter-menu__section-title {
  padding: var(--hs-space-8) var(--hs-space-12);
  background: var(--hs-background);
  color: var(--hs-text-secondary);
}
.hs-table-filter-menu__option {
  padding-inline: var(--hs-space-12);
  background: var(--hs-surface);
}
.hs-table-filter-menu__option :deep(.v-list-item__overlay) {
  display: none;
}
.hs-table-filter-menu__option:focus-visible {
  outline: 2px solid var(--hs-primary);
  outline-offset: -2px;
}
.hs-table-filter-menu__option-label {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
  white-space: normal;
  overflow-wrap: anywhere;
}
.hs-table-filter-menu__check--hidden {
  visibility: hidden;
}
.hs-table-filter-menu__empty {
  padding: var(--hs-space-12);
  color: var(--hs-text-secondary);
}
</style>
