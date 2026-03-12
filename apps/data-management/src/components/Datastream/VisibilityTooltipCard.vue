<template>
  <v-card
    elevation="2"
    rounded="lg"
    class="ma-0 pa-0"
    style="max-width: 480px; min-width: 300px"
  >
    <v-card-title class="px-4 py-2">
      <v-row no-gutters align="center" style="width: 100%">
        <v-col>
          <div
            class="text-h6"
            style="white-space: normal; word-break: break-word"
          >
            {{ title }}
          </div>
        </v-col>

        <v-col cols="auto">
          <v-chip
            small
            :color="isVisible ? 'green' : 'deep-orange-darken-4'"
            text-color="black"
          >
            {{ isVisible ? 'Visible' : 'Hidden' }}
          </v-chip>
        </v-col>
      </v-row>
    </v-card-title>

    <v-card-subtitle v-if="subtitle" class="px-4 pb-2">
      <strong>{{ subtitle.label }}:</strong>
      {{ subtitle.value ?? '—' }}
    </v-card-subtitle>

    <v-divider />

    <v-card-text class="py-2 px-4">
      <v-row dense>
        <template v-for="(item, i) in items" :key="i">
          <v-col cols="5" class="font-weight-medium">
            {{ item.label }}
          </v-col>
          <v-col cols="7">
            {{ item.value ?? '—' }}
          </v-col>
        </template>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
interface KV {
  label: string
  value: string | number | null
}

defineProps<{
  title: string
  subtitle?: KV
  items: KV[]
  isVisible: boolean
}>()
</script>
