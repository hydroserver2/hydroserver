<template>
  <section
    class="hs-empty-state"
    :class="{ 'hs-empty-state--compact': compact }"
  >
    <div class="hs-empty-state__content">
      <div v-if="icon" class="hs-empty-state__icon">
        <v-icon :icon="icon" size="28" />
      </div>
      <p v-if="eyebrow" class="hs-empty-state__eyebrow hs-label">
        {{ eyebrow }}
      </p>
      <h2 :class="compact ? 'hs-subheading' : 'hs-heading'">{{ title }}</h2>
      <div v-if="$slots.default" class="hs-empty-state__message">
        <slot />
      </div>
      <div v-if="$slots.actions" class="hs-empty-state__actions">
        <slot name="actions" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
defineOptions({ name: 'HsEmptyState' })

withDefaults(
  defineProps<{
    title: string
    eyebrow?: string
    icon?: string
    compact?: boolean
  }>(),
  {
    eyebrow: '',
    icon: '',
    compact: false,
  }
)
</script>

<style scoped>
.hs-empty-state {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: var(--hs-space-32);
  overflow: auto;
  background: var(--hs-background);
}

.hs-empty-state--compact {
  flex: none;
  padding: 40px var(--hs-space-20);
  color: var(--hs-text-secondary);
  text-align: center;
  background: transparent;
}

.hs-empty-state__content {
  width: 100%;
  max-width: 560px;
  color: var(--hs-text-primary);
}

.hs-empty-state--compact .hs-empty-state__content {
  color: var(--hs-text-secondary);
}

.hs-empty-state__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin-bottom: var(--hs-space-16);
  color: rgb(var(--v-theme-primary));
  background: var(--hs-surface-muted);
  border-radius: 50%;
}

.hs-empty-state__eyebrow {
  margin: 0 0 var(--hs-space-8);
  color: var(--hs-text-secondary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.hs-empty-state h2 {
  margin: 0 0 var(--hs-space-12);
  color: var(--hs-text-primary);
}

.hs-empty-state--compact h2 {
  margin-bottom: var(--hs-space-6);
}

.hs-empty-state__message {
  line-height: 1.55;
}

.hs-empty-state__actions {
  margin-top: var(--hs-space-24);
}
</style>
