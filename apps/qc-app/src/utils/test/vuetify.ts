// Minimal Vuetify instance for mount() tests.
import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'

export function createTestVuetify() {
  return createVuetify({
    icons: {
      defaultSet: 'mdi',
      aliases,
      sets: { mdi },
    },
  })
}
