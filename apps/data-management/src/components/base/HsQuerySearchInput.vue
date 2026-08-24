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
import { mdiMagnify } from '@mdi/js'

type QueryQualifier = {
  key: string
  label: string
  values: readonly string[]
}

const props = withDefaults(
  defineProps<{
    modelValue: string
    placeholder: string
    ariaLabel?: string
    qualifiers: readonly QueryQualifier[]
  }>(),
  { ariaLabel: '' }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const inputEl = ref<HTMLInputElement | null>(null)
const caret = ref(0)
const suggestionIndex = ref(0)
const suggestionsEnabled = ref(false)

const qualifierPattern = computed(() => {
  const keys = props.qualifiers
    .map(({ key }) => key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')
  return keys ? new RegExp(`(${keys}):(?:"([^"]*)"|(\\S+))`, 'gi') : null
})

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
  const pattern = qualifierPattern.value
  if (!pattern) return [{ text: raw, cls: '' }]

  const segments: { text: string; cls: string }[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  pattern.lastIndex = 0
  while ((match = pattern.exec(raw))) {
    if (match.index > lastIndex) {
      segments.push({ text: raw.slice(lastIndex, match.index), cls: '' })
    }
    const key = match[1] ?? ''
    const quoted = match[2] !== undefined
    const value = match[2] ?? match[3] ?? ''
    segments.push({ text: key, cls: 'hl-key' })
    segments.push({ text: ':', cls: 'hl-colon' })
    segments.push({
      text: quoted ? `"${value}"` : value,
      cls: value && isValidQualifierValue(key, value) ? 'hl-value-valid' : '',
    })
    lastIndex = pattern.lastIndex
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

function findTokenStart(raw: string, caretPosition: number) {
  let inQuotes = false
  let tokenStart = 0
  for (let index = 0; index < caretPosition; index += 1) {
    const character = raw[index]
    if (character === '"') inQuotes = !inQuotes
    else if (character === ' ' && !inQuotes) tokenStart = index + 1
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
  const pattern = qualifierPattern.value
  if (!pattern) return selected

  let match: RegExpExecArray | null
  pattern.lastIndex = 0
  while ((match = pattern.exec(props.modelValue))) {
    const key = (match[1] ?? '').toLocaleLowerCase()
    const value = match[2] ?? match[3] ?? ''
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
  const nextCaret = start + replacement.length
  emit(
    'update:modelValue',
    props.modelValue.slice(0, start) + replacement + props.modelValue.slice(end)
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
