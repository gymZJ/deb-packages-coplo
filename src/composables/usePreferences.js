import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from 'vuetify'
import { normalizeLocale } from '../i18n/index.js'

export function usePreferences() {
  const theme = useTheme()
  const { locale } = useI18n()
  const themePreference = ref(localStorage.getItem('coplo-theme') || 'system')
  let mediaQuery = null

  function applyTheme() {
    const dark =
      themePreference.value === 'dark' ||
      (themePreference.value === 'system' && mediaQuery?.matches)
    theme.global.name.value = dark ? 'coploDark' : 'coploLight'
  }

  function setTheme(value) {
    themePreference.value = value
    localStorage.setItem('coplo-theme', value)
    applyTheme()
  }

  function setLocale(value) {
    const normalized = normalizeLocale(value) || 'en'
    locale.value = normalized
    localStorage.setItem('coplo-locale', normalized)
  }

  watch(
    locale,
    (value) => {
      document.documentElement.lang = value
    },
    { immediate: true },
  )

  onMounted(() => {
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', applyTheme)
    applyTheme()
  })

  onBeforeUnmount(() => mediaQuery?.removeEventListener('change', applyTheme))
  return { themePreference, setTheme, setLocale }
}
