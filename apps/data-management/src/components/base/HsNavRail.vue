<template>
  <nav class="hs-nav-rail" :aria-label="ariaLabel">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="hs-nav-rail__item"
      :aria-current="modelValue === item.id ? 'page' : undefined"
      @click="emit('update:modelValue', item.id)"
    >
      <span
        class="hs-nav-rail__pill"
        :style="modelValue === item.id ? activePillStyle(item) : undefined"
      >
        <v-icon
          :icon="item.icon"
          size="22"
          :style="modelValue === item.id ? activeTextStyle(item) : undefined"
        />
        <span v-if="item.badge" class="hs-nav-rail__badge hs-label">
          {{ item.badge }}
        </span>
      </span>
      <span
        class="hs-nav-rail__label hs-text-2xs"
        :class="{ 'font-weight-semibold': modelValue === item.id }"
        :style="modelValue === item.id ? activeTextStyle(item) : undefined"
      >
        {{ item.label }}
      </span>
    </button>
  </nav>
</template>

<script setup lang="ts">
type HsNavRailItem = {
  id: string
  label: string
  icon: string
  badge?: number
  activeColor?: string
  activeBackground?: string
}

withDefaults(
  defineProps<{
    items: HsNavRailItem[]
    modelValue: string
    ariaLabel?: string
  }>(),
  { ariaLabel: 'Sections' }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const activeTextStyle = (item: HsNavRailItem) => ({
  color: item.activeColor || 'rgb(var(--v-theme-primary))',
})

const activePillStyle = (item: HsNavRailItem) => ({
  background: item.activeBackground || 'rgba(var(--v-theme-primary), 0.12)',
})
</script>

<style scoped>
.hs-nav-rail {
  display: flex;
  flex-shrink: 0;
  flex-direction: column;
  align-items: center;
  width: 88px;
  padding: var(--hs-space-16) 0;
  background: var(--hs-surface-muted);
  border-right: 1px solid var(--hs-border);
}

.hs-nav-rail__item {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-4);
  align-items: center;
  width: 100%;
  padding: var(--hs-space-8) var(--hs-space-4);
  font-family: inherit;
  cursor: pointer;
  background: transparent;
  border: 0;
}

.hs-nav-rail__item:hover .hs-nav-rail__pill {
  background: rgba(var(--v-theme-text-primary), 0.05);
}

.hs-nav-rail__pill {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 32px;
  border-radius: var(--hs-radius-xl);
  transition: background 0.15s;
}

.hs-nav-rail__badge {
  position: absolute;
  top: 1px;
  right: var(--hs-space-4);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 3px;
  color: white;
  line-height: 1;
  background: var(--hs-danger);
  border-radius: var(--hs-radius-pill);
}

.hs-nav-rail__label {
  color: var(--hs-text-secondary);
  line-height: 1.2;
  text-align: center;
}

@media (max-width: 700px) {
  .hs-nav-rail {
    flex-direction: row;
    width: 100%;
    padding: var(--hs-space-4) var(--hs-space-8);
    overflow-x: auto;
    border-right: 0;
    border-bottom: 1px solid var(--hs-border);
  }

  .hs-nav-rail__item {
    width: auto;
    min-width: 88px;
  }
}
</style>
