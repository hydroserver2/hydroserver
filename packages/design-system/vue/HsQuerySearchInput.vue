<template>
  <div class="hs-query-search">
    <v-icon :icon="mdiMagnify" size="16" class="hs-query-search__icon" />
    <div class="hs-query-search__highlight hs-text-sm" aria-hidden="true">
      <span
        v-for="(segment, index) in highlightSegments"
        :key="index"
        :class="segment.cls"
        >{{ segment.text }}</span
      >
    </div>
    <input
      ref="inputEl"
      :value="modelValue"
      :placeholder="placeholder"
      :aria-label="ariaLabel || placeholder"
      class="hs-query-search__input hs-text-sm"
      autocomplete="off"
      spellcheck="false"
      role="combobox"
      aria-autocomplete="list"
      :aria-expanded="!!activeSuggestion"
      @input="onInput"
      @click="syncCaret"
      @keyup="syncCaret"
      @keydown="onKeydown"
      @focus="onFocus"
      @blur="suggestionsEnabled = false"
    />
    <button
      v-if="modelValue"
      type="button"
      class="hs-query-search__clear"
      aria-label="Clear search and filters"
      @mousedown.prevent
      @click="clearSearch"
    >
      <v-icon :icon="mdiClose" size="16" />
    </button>
  </div>

  <Teleport to="body">
    <div
      v-if="activeSuggestion && activeSuggestion.items.length"
      class="hs-query-search-popover"
      :style="suggestionStyle"
      role="listbox"
    >
      <div class="hs-query-search-popover__title">
        {{
          activeSuggestion.type === 'key'
            ? 'Filter by…'
            : `${activeSuggestion.label} values`
        }}
      </div>
      <button
        v-for="(item, index) in activeSuggestion.items"
        :key="item"
        type="button"
        class="hs-query-search-popover__option"
        :class="{
          'hs-query-search-popover__option--active': index === suggestionIndex,
        }"
        role="option"
        :aria-selected="index === suggestionIndex"
        @mousedown.prevent="applySuggestion(item)"
      >
        {{ item }}{{ activeSuggestion.type === 'key' ? ':' : '' }}
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { mdiClose, mdiMagnify } from '@mdi/js'
import type { HsQueryQualifier } from './types'
import { queryQualifierTokens } from './querySearch'

defineOptions({ name: 'HsQuerySearchInput' })

const props = withDefaults(
  defineProps<{
    modelValue: string
    placeholder: string
    ariaLabel?: string
    qualifiers: readonly HsQueryQualifier[]
  }>(),
  { ariaLabel: '' }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  clear: []
}>()

const inputEl = ref<HTMLInputElement | null>(null)
const caret = ref(0)
const suggestionIndex = ref(0)
const suggestionsEnabled = ref(false)

const qualifierTokens = computed(() =>
  queryQualifierTokens(props.modelValue, props.qualifiers)
)

const qualifierByKey = computed(
  () =>
    new Map(
      props.qualifiers.map((qualifier) => [
        qualifier.key.toLocaleLowerCase(),
        qualifier,
      ])
    )
)

function isValidQualifierValue(key: string, value: string) {
  const qualifier = qualifierByKey.value.get(key.toLocaleLowerCase())
  if (!qualifier) return false
  return qualifier.values.some(
    (item) => item.toLocaleLowerCase() === value.toLocaleLowerCase()
  )
}

const highlightSegments = computed(() => {
  const raw = props.modelValue
  const segments: { text: string; cls: string }[] = []
  let lastIndex = 0
  for (const token of qualifierTokens.value) {
    if (token.start > lastIndex) {
      segments.push({ text: raw.slice(lastIndex, token.start), cls: '' })
    }
    const { key, value } = token
    segments.push({ text: key, cls: 'hl-key' })
    segments.push({ text: ':', cls: 'hl-colon' })
    segments.push({
      text: raw.slice(token.start + key.length + 1, token.end),
      cls: value && isValidQualifierValue(key, value) ? 'hl-value-valid' : '',
    })
    lastIndex = token.end
  }
  if (lastIndex < raw.length) {
    segments.push({ text: raw.slice(lastIndex), cls: '' })
  }
  return segments
})

const suggestionStyle = computed(() => {
  const input = inputEl.value
  if (!input) return {}
  const rect = input.getBoundingClientRect()
  return { top: `${rect.bottom + 4}px`, left: `${rect.left}px` }
})

function syncCaret() {
  const input = inputEl.value
  if (input) caret.value = input.selectionStart ?? input.value.length
}

function onInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
  syncCaret()
  suggestionsEnabled.value = true
}

function onFocus() {
  suggestionsEnabled.value = true
  syncCaret()
}

function clearSearch() {
  suggestionsEnabled.value = false
  caret.value = 0
  emit('update:modelValue', '')
  emit('clear')
  nextTick(() => inputEl.value?.focus())
}

function findTokenStart(raw: string, caretPosition: number) {
  let inQuotes = false
  let tokenStart = 0
  for (let index = 0; index < caretPosition; index += 1) {
    const character = raw[index]
    if (character === '"') inQuotes = !inQuotes
    else if (/\s/.test(character ?? '') && !inQuotes) {
      const token = raw.slice(tokenStart, caretPosition)
      const colon = token.indexOf(':')
      const qualifier = qualifierByKey.value.get(
        token.slice(0, colon).toLocaleLowerCase()
      )
      const query = token.slice(colon + 1).toLocaleLowerCase()
      // Keep suggesting a name as the user types beyond its first word.
      if (
        colon >= 0 &&
        qualifier?.values.some((value) =>
          value.toLocaleLowerCase().includes(query)
        )
      )
        continue
      tokenStart = index + 1
    }
  }
  return tokenStart
}

const currentToken = computed(() => {
  const raw = props.modelValue
  const end = Math.min(caret.value, raw.length)
  const start = findTokenStart(raw, end)
  return { start, end, text: raw.slice(start, end) }
})

const selectedQualifierValues = computed(() => {
  const selected = new Map<string, string[]>()
  for (const token of qualifierTokens.value) {
    // The value under the caret is being edited, not a duplicate selection.
    if (token.start <= caret.value && caret.value <= token.end) continue
    const key = token.key.toLocaleLowerCase()
    const value = token.value
    if (value) selected.set(key, [...(selected.get(key) ?? []), value])
  }
  return selected
})

const activeSuggestion = computed(() => {
  if (!suggestionsEnabled.value) return null
  const { text, start, end } = currentToken.value
  if (!text) return null

  const colonIndex = text.indexOf(':')
  if (colonIndex === -1) {
    const query = text.toLocaleLowerCase()
    const items = props.qualifiers
      .map(({ key }) => key)
      .filter((key) => key.toLocaleLowerCase().startsWith(query))
    return items.length
      ? { type: 'key' as const, key: '', label: '', items, start, end }
      : null
  }

  const key = text.slice(0, colonIndex).toLocaleLowerCase()
  const qualifier = qualifierByKey.value.get(key)
  if (!qualifier?.values.length) return null

  let valueQuery = text.slice(colonIndex + 1)
  if (valueQuery.startsWith('"')) valueQuery = valueQuery.slice(1)
  if (valueQuery.endsWith('"')) valueQuery = valueQuery.slice(0, -1)
  const query = valueQuery.toLocaleLowerCase()
  const selected = selectedQualifierValues.value.get(key) ?? []
  const items = qualifier.values.filter(
    (value) =>
      !selected.includes(value) && value.toLocaleLowerCase().includes(query)
  )

  return items.length
    ? {
        type: 'value' as const,
        key: qualifier.key,
        label: qualifier.label,
        items,
        start,
        end,
      }
    : null
})

watch(activeSuggestion, () => {
  suggestionIndex.value = 0
})

function replaceCurrentToken(replacement: string) {
  const { start, end } = currentToken.value
  const token = qualifierTokens.value.find((item) => item.start === start)
  const replacementEnd = Math.max(end, token?.end ?? end)
  const suffix = props.modelValue.slice(replacementEnd)
  const nextCaret = start + replacement.length
  emit(
    'update:modelValue',
    props.modelValue.slice(0, start) +
      replacement +
      (replacement.endsWith(' ') ? suffix.replace(/^\s+/, '') : suffix)
  )
  nextTick(() => {
    const input = inputEl.value
    if (!input) return
    input.focus()
    input.setSelectionRange(nextCaret, nextCaret)
    caret.value = nextCaret
  })
}

function quoteIfNeeded(value: string) {
  return /\s/.test(value) ? `"${value}"` : value
}

function applySuggestion(item: string) {
  const suggestion = activeSuggestion.value
  if (!suggestion) return
  replaceCurrentToken(
    suggestion.type === 'key'
      ? `${item}:`
      : `${suggestion.key}:${quoteIfNeeded(item)} `
  )
}

function onKeydown(event: KeyboardEvent) {
  const suggestion = activeSuggestion.value
  if (!suggestion) return
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
    applySuggestion(suggestion.items[suggestionIndex.value] ?? '')
  } else if (event.key === 'Escape') {
    suggestionsEnabled.value = false
  }
}
</script>
