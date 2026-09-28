import { createI18n } from 'vue-i18n'
import en from './messages/en.js'
import zhCN from './messages/zh-CN.js'
import zhTW from './messages/zh-TW.js'

export const supportedLocales = Object.freeze([
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'en', label: 'English' },
])

export function normalizeLocale(locale) {
  if (!locale) return null
  const normalized = locale.replace('_', '-').toLowerCase()
  if (normalized === 'zh') return 'zh-CN'
  if (
    normalized.startsWith('zh-tw') ||
    normalized.startsWith('zh-hk') ||
    normalized.startsWith('zh-mo') ||
    normalized.startsWith('zh-hant')
  ) {
    return 'zh-TW'
  }
  if (normalized.startsWith('zh')) return 'zh-CN'
  if (normalized.startsWith('en')) return 'en'
  return null
}

function initialLocale() {
  const saved = normalizeLocale(localStorage.getItem('coplo-locale'))
  if (saved) return saved
  for (const candidate of navigator.languages ?? [navigator.language]) {
    const matched = normalizeLocale(candidate)
    if (matched) return matched
  }
  return 'en'
}

export default createI18n({
  legacy: false,
  locale: initialLocale(),
  fallbackLocale: 'en',
  messages: { 'zh-CN': zhCN, 'zh-TW': zhTW, en },
})
