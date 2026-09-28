import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

export default createVuetify({
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: { mdi },
  },
  theme: {
    defaultTheme: 'coploLight',
    themes: {
      coploLight: {
        dark: false,
        colors: {
          background: '#f5f6f8',
          surface: '#ffffff',
          'surface-variant': '#f0f2f5',
          primary: '#315efb',
          secondary: '#667085',
          error: '#f04438',
          outline: '#dfe3e8',
        },
      },
      coploDark: {
        dark: true,
        colors: {
          background: '#0f1115',
          surface: '#15181e',
          'surface-variant': '#1b1f27',
          primary: '#8ca3ff',
          secondary: '#98a2b3',
          error: '#f97066',
          outline: '#2b313b',
        },
      },
    },
  },
  defaults: {
    VBtn: { elevation: 0, rounded: 'md' },
    VCard: { elevation: 0, rounded: 'lg' },
    VTextField: { density: 'compact', variant: 'outlined' },
  },
})
