<script setup lang="ts">
// Temporary v2-release notices, turned on per page with frontmatter:
//   v1Notice: true          -> "the v1 docs have moved" notice
//   playgroundNotice: true  -> "the playground still runs v1" notice
//   v1Page: false           -> the page has no v1 counterpart, so don't link to one
// Remove a notice by deleting its frontmatter key from each page (or this component).
import { computed } from "vue";
import { useData, withBase } from "vitepress";

const { frontmatter, page } = useData();

const showV1 = computed(() => frontmatter.value.v1Notice === true);
const showPlayground = computed(() => frontmatter.value.playgroundNotice === true);
const hasV1Page = computed(() => frontmatter.value.v1Page !== false);

// The v1 docs are a separate build served at /v1/, so links to them must
// bypass the SPA router (target="_self" forces a full page load).
const v1Root = withBase("/v1/");
const v1PageUrl = computed(() => {
  const path = page.value.relativePath
    .replace(/(^|\/)index\.md$/, "$1")
    .replace(/\.md$/, ".html");
  return v1Root + path;
});
</script>

<template>
  <div v-if="showV1 || showPlayground" class="version-notices">
    <div v-if="showV1" class="version-notice info">
      <p class="version-notice-title">Looking for the HydroServer v1 docs?</p>
      <p>
        These docs now cover HydroServer v2. The v1 docs have moved to
        <a :href="v1Root" target="_self">hydroserver.org/v1</a> and are still
        available.
        <template v-if="hasV1Page">
          <a :href="v1PageUrl" target="_self">View the v1 version of this page</a>.
        </template>
      </p>
    </div>
    <div v-if="showPlayground" class="version-notice warning">
      <p class="version-notice-title">
        The playground hasn't been updated to HydroServer v2 yet
      </p>
      <p>
        This page uses
        <a href="https://playground.hydroserver.org">playground.hydroserver.org</a>
        in its steps or examples, but the playground is still running HydroServer
        v1. Until it's updated, the v2 features described here won't work there.
        Use a HydroServer v2 instance<template v-if="hasV1Page">, or follow the
          <a :href="v1PageUrl" target="_self">v1 version of this page</a> to use
          the playground</template>.
      </p>
    </div>
  </div>
</template>

<style scoped>
.version-notices {
  margin-bottom: 24px;
}

.version-notice {
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: var(--vp-custom-block-font-size);
  line-height: 24px;
}

.version-notice + .version-notice {
  margin-top: 12px;
}

.version-notice p {
  margin: 0;
}

.version-notice p + p {
  margin-top: 4px;
}

.version-notice-title {
  font-weight: 600;
}

.version-notice a {
  font-weight: 500;
  text-decoration: underline;
  text-underline-offset: 2px;
  transition: opacity 0.25s;
}

.version-notice a:hover {
  opacity: 0.75;
}

.version-notice.info {
  border-color: var(--vp-custom-block-info-border);
  color: var(--vp-custom-block-info-text);
  background-color: var(--vp-custom-block-info-bg);
}

.version-notice.info a {
  color: var(--vp-c-brand-1);
}

.version-notice.warning {
  border-color: var(--vp-custom-block-warning-border);
  color: var(--vp-custom-block-warning-text);
  background-color: var(--vp-custom-block-warning-bg);
}

.version-notice.warning a {
  color: var(--vp-custom-block-warning-text);
}
</style>
