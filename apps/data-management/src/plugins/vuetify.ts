import 'vuetify/styles'

import { createVuetify, ThemeDefinition } from 'vuetify'
import { VBtn } from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { md3 } from 'vuetify/blueprints'
import { mdiPlus } from '@mdi/js'
// add this import
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'

// Material theme Colors: https://vuetifyjs.com/en/styles/colors/
const theme: ThemeDefinition = {
  dark: false,
  colors: {
    background: '#FAFAFA', // grey-lighten-5
    surface: '#FFFFFF', // white
    primary: '#2196F3', // blue
    secondary: '#4CAF50', // green
    default: '#757575', // grey-darken-1
    delete: '#F44336', // red
    error: '#F44336', // red
    info: '#03A9F4', // light-blue
    success: '#4CAF50', // green
    warning: '#FF9800', // orange
    navbar: '#272e3d',
  },
}

const darkTheme: ThemeDefinition = {
  dark: true,
  colors: {
    background: '#18212a',
    surface: '#18212a',
    primary: '#2196F3',
    secondary: '#4CAF50',
    default: '#cfd8dc',
    delete: '#F44336',
    error: '#F44336',
    info: '#03A9F4',
    success: '#4CAF50',
    warning: '#FF9800',
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
}

export default createVuetify({
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
      dark: darkTheme,
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
