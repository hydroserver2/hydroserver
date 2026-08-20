<template>
  <div class="hs-master-detail">
    <aside
      class="hs-master-detail__sidebar"
      :data-testid="sidebarTestId || undefined"
    >
      <slot name="sidebar" />
    </aside>
    <div class="hs-master-detail__content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    sidebarTestId?: string
  }>(),
  { sidebarTestId: '' }
)
</script>

<style scoped>
.hs-master-detail {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--hs-background);
}

.hs-master-detail__sidebar {
  position: relative;
  display: flex;
  flex-shrink: 0;
  flex-direction: column;
  width: 260px;
  min-height: 0;
  background: var(--hs-surface-muted);
  border-right: 1px solid var(--hs-border);
}

.hs-master-detail__content {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

@media (max-width: 700px) {
  .hs-master-detail {
    flex-direction: column;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    overflow: visible;
  }

  .hs-master-detail__sidebar {
    width: 100%;
    max-width: 100%;
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--hs-border);
  }

  .hs-master-detail__content {
    width: 100%;
    max-width: 100%;
    overflow: visible;
  }
}
</style>
