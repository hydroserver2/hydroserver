<template>
  <div class="hs-stat-card">
    <div class="hs-stat-card__header">
      <span class="hs-stat-card__icon">
        <v-icon :icon="icon" size="14" />
      </span>
      <span class="hs-stat-card__label hs-label">{{ label }}</span>
    </div>
    <div
      class="hs-stat-card__value hs-text-xl hs-font-data"
      :data-testid="testId"
    >
      {{ value ?? '—' }}
    </div>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'HsStatCard' })

defineProps<{
  icon: string
  label: string
  value: number | string | null
  testId?: string
}>()
</script>
