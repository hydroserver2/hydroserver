<template>
  <div
    class="hs-selection-list__item"
    :class="{
      'is-selected': selected,
      'hs-selection-list__item--with-actions': !!$slots.actions,
      'hs-selection-list__item--with-status': !!statusColor,
    }"
  >
    <span
      v-if="statusColor"
      class="hs-selection-list-item__status"
      :style="{ background: statusColor }"
      aria-hidden="true"
    />

    <button
      type="button"
      class="hs-selection-list__body"
      :aria-label="ariaLabel || `Select ${title}`"
      :aria-current="selected ? 'true' : undefined"
      @click="emit('select')"
    >
      <div class="hs-selection-list__title hs-title">{{ title }}</div>
      <div v-if="$slots.metadata" class="hs-selection-list__meta hs-text-2xs">
        <span class="hs-selection-list__meta-text">
          <slot name="metadata" />
        </span>
      </div>
    </button>

    <span
      v-if="badge !== undefined && badge !== null"
      class="hs-selection-list-item__badge hs-label"
    >
      {{ badge }}
    </span>

    <span v-if="$slots.actions" class="hs-selection-list__actions">
      <slot name="actions" />
    </span>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    selected?: boolean
    ariaLabel?: string
    statusColor?: string
    badge?: string | number | null
  }>(),
  {
    selected: false,
    ariaLabel: '',
    statusColor: '',
    badge: null,
  }
)

const emit = defineEmits<{
  select: []
}>()
</script>

<style scoped>
.hs-selection-list-item__status {
  flex-shrink: 0;
  width: 7px;
  height: 7px;
  margin-top: 5px;
  border-radius: 50%;
}

.hs-selection-list-item__badge {
  padding: 1px var(--hs-space-6);
  color: var(--hs-danger);
  background: var(--hs-danger-bg);
  border-radius: var(--hs-radius-pill);
}
</style>
