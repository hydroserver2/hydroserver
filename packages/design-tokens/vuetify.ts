import 'vuetify/styles'

import { createVuetify, type ThemeDefinition } from 'vuetify'
import { VBtn } from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { md3 } from 'vuetify/blueprints'
import { mdiPlus } from '@mdi/js'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'

// HydroServer's shared palette and semantic roles. Keep the literal beside its
// role so the complete color system can be reviewed and changed in one place.
const theme: ThemeDefinition = {
  dark: false,
  colors: {
    'text-primary': '#1C1B1F',
    'text-secondary': '#49454F',
    'text-muted': '#9CA3AF',
    background: '#F4F7FA',
    surface: '#FFFFFF',
    'surface-subtle': '#FCFDFF',
    'surface-muted': '#EEF3F8',
    'surface-floating': '#FFFFFFF5',
    border: '#CED8E2',
    'input-border': '#CAC4D0',
    primary: '#32649C',
    secondary: '#66AE5C',
    default: '#757575',
    danger: '#B3261E',
    'danger-bg': '#FFEBEE',
    delete: '#F44336',
    error: '#F44336',
    info: '#03A9F4',
    success: '#66AE5C',
    warning: '#FF9800',
    navbar: '#272E3D',
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
