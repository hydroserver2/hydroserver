<template>
  <div class="hs-table-summary">
    <div class="hs-table-summary__heading">
      <div v-if="$slots.badge" class="hs-table-summary__badge">
        <slot name="badge" />
      </div>
      <span class="hs-subheading hs-table-summary__title">{{ title }}</span>
      <div v-if="$slots.action" class="hs-table-summary__action">
        <slot name="action" />
      </div>
    </div>
    <ul
      v-if="$slots.details || details.length"
      class="hs-table-summary__details hs-text-sm"
    >
      <slot name="details">
        <li v-for="(detail, index) in details" :key="index">{{ detail }}</li>
      </slot>
    </ul>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; details: string[] }>()
</script>

<style scoped>
.hs-table-summary {
  min-width: 0;
  padding-block: var(--hs-space-12);
}
.hs-table-summary__heading {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
}
.hs-table-summary__badge,
.hs-table-summary__action {
  display: flex;
  flex-shrink: 0;
  align-items: center;
}
.hs-table-summary__title {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--hs-text-primary);
}
.hs-table-summary__details {
  display: flex;
  gap: var(--hs-space-8);
  margin-top: var(--hs-space-4);
  padding: 0;
  list-style: none;
  color: var(--hs-text-secondary);
}
.hs-table-summary__details :deep(> li) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hs-table-summary__details :deep(> li:not(:last-child)) {
  flex-shrink: 0;
  max-width: 35%;
}
.hs-table-summary__details :deep(> li + li)::before {
  flex-shrink: 0;
  content: '·';
  margin-right: var(--hs-space-8);
}
@media (max-width: 40rem) {
  .hs-table-summary__heading {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .hs-table-summary__badge {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
</style>
