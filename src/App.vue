<script setup>
import { useI18n } from 'vue-i18n'
import { supportedLocales } from './i18n/index.js'
import { usePreferences } from './composables/usePreferences.js'

const { t, locale } = useI18n()
const { themePreference, setTheme, setLocale } = usePreferences()

const repositoryUrl = 'https://github.com/gymZJ/deb-packages-coplo'
const issuesUrl = `${repositoryUrl}/issues`
const emailUrl = 'mailto:dayearnew@gmail.com'
const themeItems = [
  { value: 'system', icon: 'mdi-theme-light-dark', label: 'app.themeSystem' },
  { value: 'light', icon: 'mdi-white-balance-sunny', label: 'app.themeLight' },
  { value: 'dark', icon: 'mdi-weather-night', label: 'app.themeDark' },
]
</script>

<template>
  <v-app>
    <v-app-bar class="app-bar" flat height="58">
      <v-container class="app-shell d-flex align-center px-4">
        <router-link to="/" class="brand-link d-flex align-center ga-2">
          <v-icon icon="mdi-package-variant-closed" size="20" color="primary" />
          <span>{{ t('app.title') }}</span>
        </router-link>
        <v-spacer />

        <v-menu location="bottom end">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              variant="text"
              size="small"
              :icon="
                themePreference === 'dark'
                  ? 'mdi-weather-night'
                  : themePreference === 'light'
                    ? 'mdi-white-balance-sunny'
                    : 'mdi-theme-light-dark'
              "
              :aria-label="t('app.themeSystem')"
            />
          </template>
          <v-list density="compact" min-width="150">
            <v-list-item
              v-for="item in themeItems"
              :key="item.value"
              :prepend-icon="item.icon"
              :title="t(item.label)"
              :active="themePreference === item.value"
              @click="setTheme(item.value)"
            />
          </v-list>
        </v-menu>

        <v-menu location="bottom end">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              icon="mdi-translate"
              variant="text"
              size="small"
              :aria-label="t('app.language')"
            />
          </template>
          <v-list density="compact" min-width="150">
            <v-list-item
              v-for="item in supportedLocales"
              :key="item.value"
              :title="item.label"
              :active="locale === item.value"
              @click="setLocale(item.value)"
            />
          </v-list>
        </v-menu>

        <v-btn
          icon="mdi-github"
          variant="text"
          size="small"
          :href="repositoryUrl"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="GitHub"
        />
      </v-container>
    </v-app-bar>

    <v-main>
      <router-view />
      <footer class="site-footer">
        <span>{{ t('app.feedback') }}</span>
        <a
          :href="issuesUrl"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="t('app.issues')"
        >
          <v-icon icon="mdi-github" size="18" />
        </a>
        <a :href="emailUrl" :aria-label="t('app.email')">
          <v-icon icon="mdi-email-outline" size="18" />
        </a>
      </footer>
    </v-main>
  </v-app>
</template>
