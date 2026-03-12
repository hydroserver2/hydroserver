<template>
  <v-toolbar color="blue-darken-2">
    <v-autocomplete
      class="mx-2"
      density="compact"
      v-model="selectedKey"
      :items="Object.keys(tags)"
      label="Key"
      clearable
      @click:clear="clear"
      hide-details
      rounded="xl"
    />

    <v-autocomplete
      class="mr-2"
      density="compact"
      v-model="selectedTagValues"
      :items="tags[selectedKey]"
      label="Value"
      multiple
      clearable
      :disabled="!selectedKey"
      hide-details
      rounded="xl"
    />

    <v-checkbox
      v-model="currentColor"
      @change="updateColors"
      color="primary"
      label="Show legend"
      :disabled="!selectedKey"
      hide-details
    />

    <v-btn
      class="mx-2"
      color="white-darken-2"
      @click="clear"
      rounded="xl"
      variant="outlined"
      :append-icon="mdiClose"
      >Clear filters</v-btn
    >
  </v-toolbar>
</template>

<script setup lang="ts">
import { useWorkspaceTags } from '@/composables/useWorkspaceTags'
import { mdiClose } from '@mdi/js'
import { ref, watch } from 'vue'

const { tags } = useWorkspaceTags()

const emit = defineEmits(['filter', 'update:useColors'])
const props = defineProps({
  useColors: Boolean,
})

const selectedKey = ref('')
const selectedTagValues = ref<string[]>([])
const currentColor = ref(props.useColors)

const updateColors = () => {
  emit('update:useColors', currentColor.value)
  emitFilteredTags()
}

const emitFilteredTags = () => {
  emit('filter', { key: selectedKey.value, values: selectedTagValues.value })
}

const clear = () => {
  selectedKey.value = ''
  selectedTagValues.value = []
}

watch(selectedKey, () => {
  selectedTagValues.value = []
  emitFilteredTags()
})

watch(selectedTagValues, () => {
  emitFilteredTags()
})
</script>
