<template>
  <v-timeline-item
    fill-dot
    size="x-small"
    width="100%"
    :icon="MARKERS[kind].icon"
    :icon-color="MARKERS[kind].color"
    class="qc-timeline__item"
    :class="[MARKERS[kind].modifier, { 'qc-timeline__item--viewed': viewed }]"
  >
    <slot />
  </v-timeline-item>
</template>

<script setup lang="ts">
/**
 * One node of a session timeline: a session, or the "start a new session"
 * action that heads the chooser's timeline. Shared by the editor's session
 * list and the "Start editing" chooser.
 */

defineProps<{
  kind: 'in_progress' | 'committed' | 'new'
  /** The session on screen. */
  viewed?: boolean
}>()

const MARKERS = {
  in_progress: {
    icon: 'mdi-pencil',
    color: 'warning',
    modifier: 'qc-timeline__item--active',
  },
  committed: {
    icon: 'mdi-check',
    color: 'success',
    modifier: 'qc-timeline__item--done',
  },
  new: { icon: 'mdi-plus', color: 'primary', modifier: 'qc-timeline__item--new' },
}
</script>

<style scoped>
/* Markers: Vuetify's is a saturated disc ringed in surface-light with the
   glyph flush to its edge. Flatten it to a tonal marker with room for the
   icon, nudged onto the title's row. */
.qc-timeline__item :deep(.v-timeline-divider__dot) {
  width: 20px;
  height: 20px;
  margin-block-start: 4px;
  background: rgb(var(--v-theme-surface));
  box-shadow: none;
}

/* `.v-icon` declares the multiplier on itself, so it has to be set there. */
.qc-timeline__item :deep(.v-timeline-divider__inner-dot .v-icon) {
  --v-icon-size-multiplier: 0.75;
}

.qc-timeline__item--active :deep(.v-timeline-divider__inner-dot) {
  background: rgba(var(--v-theme-warning), 0.16);
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-warning), 0.35);
}

.qc-timeline__item--done :deep(.v-timeline-divider__inner-dot) {
  background: rgba(var(--v-theme-success), 0.16);
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-success), 0.35);
}

.qc-timeline__item--new :deep(.v-timeline-divider__inner-dot) {
  background: rgba(var(--v-theme-primary), 0.16);
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.35);
}

/* Every session reads as its own container, so the unselected ones don't
   float loose against the timeline rail. The card padding replaces Vuetify's
   body inset, so the gap to the rail comes back as a margin. */
.qc-timeline__item :deep(.v-timeline-item__body) {
  margin-inline-start: 10px;
  border-radius: 6px;
  padding: 6px 8px;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  background-color: rgba(var(--v-theme-on-surface), 0.02);
  transition:
    background-color 120ms ease,
    border-color 120ms ease;
}

.qc-timeline__item:hover :deep(.v-timeline-item__body) {
  background-color: rgba(var(--v-theme-primary), 0.06);
}

.qc-timeline__item--viewed :deep(.v-timeline-item__body) {
  background-color: rgba(var(--v-theme-primary), 0.12);
  border-color: rgba(var(--v-theme-primary), 0.4);
}

/* The action node heads the timeline rather than recording a session, so it
   stays flat instead of taking the session card treatment. */
.qc-timeline__item--new :deep(.v-timeline-item__body) {
  border-style: dashed;
  background-color: transparent;
}
</style>
