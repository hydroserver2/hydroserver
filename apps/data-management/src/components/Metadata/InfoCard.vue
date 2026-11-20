<template>
  <v-card elevation="2" rounded="lg" class="metadata-info-card ma-0 pa-0">
    <v-card-title class="px-4 py-2">
      <v-row no-gutters align="center" class="w-100">
        <v-col>
          <div class="hs-subheading metadata-info-card__title">
            {{ title }}
          </div>
        </v-col>

        <v-col cols="auto">
          <v-chip small :color="isWorkspace ? 'primary' : 'default'">
            {{ isWorkspace ? 'Workspace' : 'System' }}
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
  isWorkspace: boolean
}>()
</script>

<style scoped>
.metadata-info-card {
  min-width: 300px;
  max-width: 480px;
}

.metadata-info-card__title {
  overflow-wrap: anywhere;
}
</style>
