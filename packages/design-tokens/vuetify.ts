import 'vuetify/styles'

import { createVuetify, type ThemeDefinition } from 'vuetify'
import { VBtn } from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { md3 } from 'vuetify/blueprints'
import { mdiPlus } from '@mdi/js'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import { hexColors } from './colors'

// HydroServer's shared light theme and its Vuetify-specific semantic roles.
const theme: ThemeDefinition = {
  dark: false,
  colors: {
    // Vuetify 4's theme parser does not yet accept OKLCH, so its adapter uses
    // the shared palette's equivalent hexadecimal export.
    background: hexColors.neutral[50],
    surface: hexColors.neutral[0],
    'surface-subtle': hexColors.neutral[25],
    'surface-muted': hexColors.neutral[100],
    border: hexColors.neutral[300],
    primary: hexColors.blue[600],
    secondary: hexColors.green[500],
    default: '#757575', // grey-darken-1
    delete: '#F44336', // red
    error: '#F44336', // red
    info: '#03A9F4', // light-blue
    success: hexColors.green[500],
    warning: '#FF9800', // orange
    navbar: '#272e3d',
  },
}

const textFieldAttrs = {
  variant: 'outlined',
}

const btnAttrs = {
  color: 'primary',
  style: 'text-transform: none;', // Remove uppercase text
  rounded: 'xl',
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
    VBtnPrimary: VBtn,
    VBtnSecondary: VBtn,
    VBtnCancel: VBtn,
    VBtnDelete: VBtn,
    VBtnAdd: VBtn,
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
    VBtnPrimary: {
      ...btnAttrs,
      color: 'primary',
      // Primary actions are rectangular with rounded corners, not pills.
      rounded: 'lg',
    },
    VBtnSecondary: {
      ...btnAttrs,
      color: 'secondary',
    },
    VBtnDelete: {
      ...btnAttrs,
      color: 'delete',
    },
    VBtnCancel: {
      ...btnAttrs,
      color: 'grey',
      variant: 'outlined',
    },
    VBtnAdd: {
      ...btnAttrs,
      color: 'secondary',
      prependIcon: mdiPlus,
      rounded: true,
      variant: 'elevated',
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
