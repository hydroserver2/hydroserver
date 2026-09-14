<template>
  <v-defaults-provider :defaults="FIELD_DEFAULTS">
    <div class="task-form">
      <slot />
    </div>
  </v-defaults-provider>
</template>

<script setup lang="ts">
/*
 * The vertical rhythm every orchestration task form shares.
 *
 * Vuetify reserves a fixed strip under each field for validation messages, so
 * a stack of fields and non-field controls (checkboxes, dividers, the datastream
 * selector) ends up unevenly spaced. Collapsing that strip until a message
 * exists lets one gap own the spacing for the whole form.
 */
const FIELD_DEFAULTS = {
  VTextField: { hideDetails: 'auto' },
  VTextarea: { hideDetails: 'auto' },
  VSelect: { hideDetails: 'auto' },
  VAutocomplete: { hideDetails: 'auto' },
  VCombobox: { hideDetails: 'auto' },
  VCheckbox: { hideDetails: 'auto' },
  VRadioGroup: { hideDetails: 'auto' },
  VInput: { hideDetails: 'auto' },
}
</script>

<style scoped>
/* `gap` spaces slotted children, so sections keep this rhythm without knowing
 * about it. */
.task-form {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-20);
}
</style>
