<template>
  <section class="task-form-section">
    <h3 v-if="title" class="task-form-section__title hs-title">
      {{ title }}
    </h3>
    <slot />
  </section>
</template>

<script setup lang="ts">
// A titled group of fields inside a task form. The heading uses a shared type
// recipe rather than a hand-rolled all-caps micro-label, and the section owns
// the spacing between its fields.
defineProps<{ title?: string }>()
</script>

<style scoped>
.task-form-section {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-16);
}

.task-form-section__title {
  color: var(--hs-text-secondary);
}
</style>
