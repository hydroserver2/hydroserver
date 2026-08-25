<template>
  <section class="hs-detail-panel">
    <header
      v-if="$slots.header || $slots.actions || $slots.accessory"
      class="hs-detail-panel__header"
    >
      <div class="hs-detail-panel__heading">
        <slot name="header" />
      </div>
      <div v-if="$slots.actions" class="hs-detail-panel__actions">
        <slot name="actions" />
      </div>
      <div v-if="$slots.accessory" class="hs-detail-panel__accessory">
        <slot name="accessory" />
      </div>
    </header>

    <div v-if="$slots.toolbar" class="hs-detail-panel__toolbar">
      <slot name="toolbar" />
    </div>

    <div
      class="hs-detail-panel__body"
      :class="{ 'hs-detail-panel__body--after-toolbar': !!$slots.toolbar }"
    >
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineOptions({ name: 'HsDetailPanel' })
</script>

<style scoped>
.hs-detail-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  background: var(--hs-surface);
}

.hs-detail-panel__header {
  display: flex;
  flex-shrink: 0;
  gap: var(--hs-space-12);
  align-items: center;
  min-height: 93px;
  padding: var(--hs-space-12) var(--hs-space-24);
  background: var(--hs-surface-subtle);
  border-bottom: 1px solid var(--hs-border);
}

.hs-detail-panel__heading {
  flex: 1;
  min-width: 0;
}

.hs-detail-panel__actions,
.hs-detail-panel__accessory {
  display: flex;
  flex-shrink: 0;
  gap: var(--hs-space-8);
  align-items: center;
}

.hs-detail-panel__toolbar {
  flex-shrink: 0;
}

.hs-detail-panel__body {
  flex: 1;
  padding: var(--hs-space-16) var(--hs-space-24);
  overflow-y: auto;
}

.hs-detail-panel__body--after-toolbar {
  padding-top: 0;
}

@media (max-width: 700px) {
  .hs-detail-panel {
    overflow: visible;
  }

  .hs-detail-panel__header {
    flex-wrap: wrap;
    min-height: auto;
    padding: var(--hs-space-12) var(--hs-space-16);
  }

  .hs-detail-panel__body {
    padding: var(--hs-space-16);
    overflow: visible;
  }
}
</style>
