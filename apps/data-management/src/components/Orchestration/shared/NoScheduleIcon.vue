<template>
  <span
    class="no-schedule-icon"
    :style="{ '--no-schedule-icon-size': iconSize }"
    aria-hidden="true"
  >
    <svg
      class="no-schedule-icon__svg"
      viewBox="0 0 24 24"
      focusable="false"
      aria-hidden="true"
    >
      <path
        class="no-schedule-icon__triangle"
        d="M7 5.5v13l10.2-6.5L7 5.5Z"
      />
      <path
        class="no-schedule-icon__slash"
        d="M18.5 4.75 5.5 19.25"
      />
    </svg>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    size?: number | string
  }>(),
  {
    size: 16,
  }
)

const iconSize = computed(() => {
  const numericSize = Number(props.size)
  return Number.isFinite(numericSize) ? `${numericSize}px` : props.size
})
</script>

<style scoped>
.no-schedule-icon {
  align-items: center;
  display: inline-flex;
  height: var(--no-schedule-icon-size);
  justify-content: center;
  line-height: 0;
  width: var(--no-schedule-icon-size);
}

.no-schedule-icon__svg {
  display: block;
  height: 100%;
  overflow: visible;
  width: 100%;
}

.no-schedule-icon__triangle {
  fill: currentColor;
}

.no-schedule-icon__slash {
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: 2.8;
}
</style>
