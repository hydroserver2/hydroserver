<template>
  <RouterLink
    v-if="to"
    :to="to"
    class="main-nav-item"
    :class="{ 'main-nav-item--active': active }"
    :aria-current="active ? 'page' : undefined"
    @click="onClick"
  >
    {{ label }}
  </RouterLink>

  <a
    v-else-if="href"
    :href="href"
    class="main-nav-item"
    :class="{ 'main-nav-item--active': active }"
    :aria-current="active ? 'page' : undefined"
    @click="onClick"
  >
    {{ label }}
  </a>

  <button
    v-else
    type="button"
    class="main-nav-item"
    :class="{ 'main-nav-item--active': active }"
    :aria-current="active ? 'page' : undefined"
    @click="onClick"
  >
    {{ label }}
  </button>
</template>

<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from 'vue-router'

defineProps<{
  label: string
  to?: RouteLocationRaw
  href?: string
  active?: boolean
  onClick?: () => void
}>()
</script>

<style scoped>
.main-nav-item {
  position: relative;
  display: inline-flex;
  align-items: center;
  align-self: stretch;
  min-height: 64px;
  padding: 0 12px;
  border: 0;
  background: transparent;
  color: var(--hs-text-secondary);
  font: inherit;
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-medium);
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.15s ease;
}

.main-nav-item::after {
  position: absolute;
  right: 12px;
  bottom: 0;
  left: 12px;
  height: 3px;
  background: rgb(var(--v-theme-primary));
  content: '';
  opacity: 0;
  transform: scaleX(0.5);
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.main-nav-item:hover,
.main-nav-item:focus-visible,
.main-nav-item--active {
  color: rgb(var(--v-theme-primary));
}

.main-nav-item--active::after {
  opacity: 1;
  transform: scaleX(1);
}

.main-nav-item:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}
</style>
