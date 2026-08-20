<template>
  <div class="hs-search" :class="{ 'hs-search--pill': shape === 'pill' }">
    <v-icon :icon="mdiMagnify" size="16" class="hs-search__icon" />
    <input
      :value="modelValue"
      :placeholder="placeholder"
      :aria-label="ariaLabel || placeholder"
      :autocomplete="autocomplete"
      :spellcheck="spellcheck"
      class="hs-search__input"
      @input="onInput"
    />
  </div>
</template>

<script setup lang="ts">
import { mdiMagnify } from '@mdi/js'

withDefaults(
  defineProps<{
    modelValue: string
    placeholder: string
    ariaLabel?: string
    autocomplete?: string
    spellcheck?: boolean
    shape?: 'rounded' | 'pill'
  }>(),
  {
    ariaLabel: '',
    autocomplete: 'off',
    spellcheck: false,
    shape: 'rounded',
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>
