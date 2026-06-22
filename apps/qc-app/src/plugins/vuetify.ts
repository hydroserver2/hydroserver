import '@mdi/font/css/materialdesignicons.css'
import '@fortawesome/fontawesome-free/css/all.css'
import 'vuetify/styles'

import { createVuetify, ThemeDefinition } from 'vuetify'
import { VBtn } from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { md3 } from 'vuetify/blueprints'

// Material theme Colors: https://vuetifyjs.com/en/styles/colors/
const light: ThemeDefinition = {
  dark: false,
  colors: {
    primary: '#2196F3', // blue
    secondary: '#4CAF50', // green
    // background: '#FAFAFA', // grey-lighten-5
    background: '#f3f7fa',
    surface: '#FFFFFF', // white
    default: '#757575', // grey-darken-1
    delete: '#F44336', // red
    error: '#F44336', // red
    info: '#03A9F4', // light-blue
    success: '#4CAF50', // green
    warning: '#FF9800', // orange
    navbar: '#272e3d',
  },
}

const dark: ThemeDefinition = {
  dark: true,
  colors: {
    primary: '#2196F3', // blue
    secondary: '#4CAF50', // green
    default: '#757575', // grey-darken-1
    delete: '#F44336', // red
    error: '#F44336', // red
    info: '#03A9F4', // light-blue
    success: '#4CAF50', // green
    warning: '#FF9800', // orange

    navbar: '#272e3d',
    surface: '#18212a',
    background: '#f3f7fa',
  },
}

const textFieldAttrs = {
  density: 'comfortable',
  variant: 'outlined',
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
    // Vuetify 4 / md3 blueprint defaults v-icon to 28px; v3 default
    // was 24px. Use 'small' (20px) to match the icon weight used
    // explicitly elsewhere in the app.
    VIcon: { size: 'small' },
    VTextField: textFieldAttrs,
    VAutocomplete: textFieldAttrs,
    VTextarea: textFieldAttrs,
    VCheckbox: textFieldAttrs,
    VSelect: textFieldAttrs,
    VTable: {
      density: 'comfortable',
    },
    VCombobox: {
      variant: 'outlined',
    },
    // VBtn: {
    //   color: 'primary',
    //   density: 'comfortable',
    //   rounded: false,
    // },
    VBtnPrimary: {
      color: 'primary',
      density: 'comfortable',
    },
    VBtnSecondary: {
      color: 'secondary',
      density: 'comfortable',
    },
    VBtnDelete: {
      color: 'delete',
      density: 'comfortable',
    },
    VBtnCancel: {
      color: 'grey',
      density: 'comfortable',
      variant: 'text',
    },
    VBtnAdd: {
      color: 'secondary',
      prependIcon: 'mdi-plus',
      rounded: true,
      density: 'comfortable',
      variant: 'elevated',
    },
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light,
      dark,
    },
    variations: {
      colors: ['primary', 'secondary', 'surface'],
      lighten: 6,
      darken: 6,
    },
  },
})
