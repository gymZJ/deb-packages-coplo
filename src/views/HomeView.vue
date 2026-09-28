<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import CodeBlock from '../components/CodeBlock.vue'
import PackageCard from '../components/PackageCard.vue'
import { repository, repositorySetupCommand } from '../config/repository.js'
import { useCatalog } from '../services/catalog.js'
import { formatDate, formatSize } from '../utils/format.js'

const { t, locale } = useI18n()
const { packages, suites, defaultSuite, loading, error, loadCatalog } = useCatalog()
const suite = ref('')
const search = ref('')

const filteredPackages = computed(() => {
  const query = search.value.trim().toLowerCase()
  return packages.value.filter((pkg) => {
    if (!query) return true
    return `${pkg.name} ${pkg.repository} ${pkg.upstreamRepository}`.toLowerCase().includes(query)
  })
})

const setupCommand = computed(() => repositorySetupCommand(suite.value))

onMounted(async () => {
  try {
    await loadCatalog()
    if (!suite.value) suite.value = defaultSuite.value
  } catch {}
})
</script>

<template>
  <v-container class="app-shell page-content px-4">
    <section class="tool-section first-section">
      <div class="section-title-row">
        <h1>{{ t('app.addSource') }}</h1>
      </div>
      <v-card border class="tool-card pa-4 pa-sm-5">
        <div class="config-grid mb-4">
          <div>
            <div class="field-label">{{ t('app.distribution') }}</div>
            <v-select
              v-model="suite"
              :items="suites"
              item-title="label"
              item-value="value"
              hide-details
              density="compact"
              variant="outlined"
            />
          </div>
        </div>
        <CodeBlock :code="setupCommand" />
        <div class="key-row mt-3">
          <span>GPG</span><code>{{ repository.fingerprint }}</code>
        </div>
      </v-card>
    </section>

    <section class="tool-section packages-section">
      <div class="packages-toolbar">
        <div class="packages-heading">
          <h2>{{ t('app.packages') }}</h2>
          <span class="result-count">{{ filteredPackages.length }}</span>
        </div>
        <v-text-field
          v-model="search"
          hide-details
          prepend-inner-icon="mdi-magnify"
          :placeholder="t('app.search')"
          class="package-search"
          clearable
        />
      </div>

      <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-3">
        {{ t('app.loadFailed') }}: {{ error }}
      </v-alert>
      <v-progress-linear v-if="loading" indeterminate class="mb-3" />

      <v-card border class="package-table-wrap d-none d-md-block">
        <v-table class="package-table">
          <thead>
            <tr>
              <th>{{ t('app.packages') }}</th>
              <th>{{ t('app.version') }}</th>
              <th>{{ t('app.source') }}</th>
              <th>{{ t('app.updated') }}</th>
              <th class="text-right">{{ t('app.size') }}</th>
              <th class="table-arrow" />
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="pkg in filteredPackages"
              :key="pkg.id"
              class="package-row"
              @click="$router.push(`/packages/${pkg.id}`)"
            >
              <td>
                <strong>{{ pkg.name }}</strong>
              </td>
              <td>
                <code>{{ pkg.version }}</code>
              </td>
              <td>{{ pkg.repository }}</td>
              <td>{{ formatDate(pkg.updatedAt, locale) }}</td>
              <td class="text-right">{{ formatSize(pkg.architectures[0]?.size) }}</td>
              <td class="table-arrow"><v-icon icon="mdi-chevron-right" size="18" /></td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <div class="d-md-none mobile-package-list">
        <PackageCard v-for="pkg in filteredPackages" :key="pkg.id" :pkg="pkg" />
      </div>
    </section>
  </v-container>
</template>
