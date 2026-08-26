import 'vuetify/styles'

import { createVuetify, type ThemeDefinition } from 'vuetify'
import { VBtn } from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { md3 } from 'vuetify/blueprints'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import { vuetifyColors } from './vuetify-colors'

// colors.css is the canonical palette. The generated adapter gives Vuetify the
// concrete values it needs to create its runtime CSS variables.
const theme: ThemeDefinition = {
  dark: false,
  colors: vuetifyColors,
}

const textFieldAttrs = {
  variant: 'outlined',
}

const btnAttrs = {
  color: 'primary',
  style: 'text-transform: none;', // Remove uppercase text
  rounded: 'lg',
}

const menuDefaults = {
  menuProps: { maxHeight: 320 },
  virtualScroll: false,
  // Disable browser/Google autofill suggestions, which overlay the dropdown
  // options and make them hard to read (see issue #420).
  autocomplete: 'off',
}

const vuetify = createVuetify({
  blueprint: md3,
  directives,
  aliases: {
    // Compatibility alias while existing non-dialog usages are migrated.
    // Do not add new uses; choose a role-specific alias instead.
    VBtnPrimary: VBtn,
    VBtnDialogAction: VBtn,
    VBtnCancel: VBtn,
    VBtnDestructive: VBtn,
    VBtnIcon: VBtn,
    VBtnPageAction: VBtn,
  },
  defaults: {
    global: {
      density: 'compact',
    },
    VToolbar: { density: 'default' },
    VDataTable: { density: 'default' },
    VTextField: textFieldAttrs,
    VAutocomplete: { ...textFieldAttrs, ...menuDefaults },
    VSelect: menuDefaults,
    VCombobox: {
      variant: 'outlined',
      ...menuDefaults,
    },
    VVirtualScroll: {
      itemHeight: 64,
      bench: 12,
      height: 320,
    },
    VTextarea: textFieldAttrs,
    VCheckbox: textFieldAttrs,
    VBtn: btnAttrs,
    VBtnPrimary: btnAttrs,
    VBtnDialogAction: {
      ...btnAttrs,
      color: 'primary',
      // Dialog actions are rectangular with rounded corners, not pills.
      rounded: 'lg',
    },
    VBtnDestructive: {
      ...btnAttrs,
      color: 'delete',
    },
    VBtnCancel: {
      ...btnAttrs,
      color: 'grey',
      variant: 'text',
    },
    VBtnIcon: {
      ...btnAttrs,
      color: 'grey',
      rounded: 'sm',
      variant: 'text',
    },
    VBtnPageAction: {
      ...btnAttrs,
      // A page-level action gets the green emphasis. Use only for the one
      // action that best advances the page's main task; dialogs keep blue
      // primary actions so their submit action remains predictable.
      color: 'secondary',
      rounded: 'sm',
      variant: 'flat',
    },
  },
  theme: {
    defaultTheme: 'theme',
    themes: {
      theme,
    },
    variations: {
      colors: ['primary', 'secondary', 'surface'],
      lighten: 6,
      darken: 6,
    },
  },
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: { mdi },
  },
})

// Vuetify merges its built-in `light` and `dark` themes into custom theme
// options. HydroServer does not offer a dark mode, so do not ship the unused
// built-in dark theme through this shared configuration.
delete vuetify.theme.themes.value.dark

export default vuetify
