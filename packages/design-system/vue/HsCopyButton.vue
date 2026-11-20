<template>
  <v-tooltip text="copy id">
    <template #activator="{ props: tooltipProps }">
      <v-btn-icon
        v-bind="{ ...$attrs, ...tooltipProps }"
        icon
        color="primary"
        size="small"
        :aria-label="`Copy ID for ${label}`"
        @click.stop="copy"
      >
        <v-icon :icon="mdiContentCopy" size="small" />
      </v-btn-icon>
    </template>
  </v-tooltip>
</template>

<script setup lang="ts">
import { mdiContentCopy } from '@mdi/js'

defineOptions({ inheritAttrs: false })
const props = defineProps<{ value: string; label: string }>()
const emit = defineEmits<{ copied: []; error: [] }>()

async function copy() {
  try {
    await navigator.clipboard.writeText(props.value)
    emit('copied')
  } catch {
    emit('error')
  }
}
</script>
