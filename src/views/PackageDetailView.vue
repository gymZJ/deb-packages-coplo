<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import CodeBlock from '../components/CodeBlock.vue'
import { useCatalog } from '../services/catalog.js'
import { formatDate, formatSize } from '../utils/format.js'

const route = useRoute()
const { t, locale } = useI18n()
const { packages, suites, loading, loadCatalog } = useCatalog()
const pkg = computed(() => packages.value.find((item) => item.id === route.params.name))
const installCommand = computed(() => (pkg.value ? `sudo apt install ${pkg.value.name}` : ''))
const artifactGroups = computed(() => {
  const groups = new Map()
  for (const artifact of pkg.value?.artifacts || []) {
    if (!groups.has(artifact.name)) groups.set(artifact.name, [])
    groups.get(artifact.name).push(artifact)
  }
  return [...groups].map(([architecture, artifacts]) => ({ architecture, artifacts }))
})
const showArchitecture = computed(() => artifactGroups.value.length > 1)

function distributionLabel(artifact) {
  const artifactSuites = artifact.suites || []
  if (!artifactSuites.length || !suites.value.length) return ''
  const allSuites = suites.value.map((suite) => suite.value)
  if (
    artifactSuites.length === allSuites.length &&
    allSuites.every((suite) => artifactSuites.includes(suite))
  ) {
    return ''
  }
  return artifactSuites
    .map((name) => suites.value.find((suite) => suite.value === name)?.label || name)
    .join(' · ')
}

onMounted(() => loadCatalog().catch(() => {}))
</script>

<template>
  <v-container v-if="pkg" class="app-shell detail-page px-4">
    <v-btn to="/" variant="text" size="small" prepend-icon="mdi-arrow-left" class="back-button">
      {{ t('app.back') }}
    </v-btn>
    <div class="detail-title-row">
      <h1>{{ pkg.name }}</h1>
      <v-btn
        :href="pkg.repositoryUrl"
        target="_blank"
        rel="noopener noreferrer"
        variant="outlined"
        size="small"
        prepend-icon="mdi-open-in-new"
        >{{ t('app.source') }}</v-btn
      >
    </div>
    <div class="detail-grid">
      <div class="detail-main-column">
        <v-card border class="detail-panel pa-4 pa-sm-5">
          <h2>{{ t('app.install') }}</h2>
          <CodeBlock :code="installCommand" class="mt-3" />
        </v-card>
        <v-card border class="detail-panel pa-4 pa-sm-5">
          <h2>{{ t('app.packages') }}</h2>
          <div class="build-groups mt-3">
            <div v-for="group in artifactGroups" :key="group.architecture" class="build-group">
              <div v-if="showArchitecture" class="build-architecture">{{ group.architecture }}</div>
              <div class="build-table">
                <a
                  v-for="artifact in group.artifacts"
                  :key="artifact.url"
                  :href="artifact.url"
                  :title="artifact.filename"
                  target="_blank"
                  class="build-row"
                >
                  <div class="build-package">
                    <div class="build-package-line">
                      <span class="build-package-name">{{ artifact.package }}</span>
                      <code>{{ artifact.version }}</code>
                    </div>
                    <div v-if="distributionLabel(artifact)" class="build-meta">
                      {{ distributionLabel(artifact) }}
                    </div>
                  </div>
                  <span class="build-size">{{ formatSize(artifact.size) }}</span>
                  <v-icon icon="mdi-download-outline" size="18" />
                </a>
              </div>
            </div>
          </div>
        </v-card>
      </div>
      <v-card border class="detail-panel facts-panel pa-4 pa-sm-5">
        <div class="fact">
          <span>{{ t('app.version') }}</span
          ><strong>{{ pkg.version }}</strong>
        </div>
        <div class="fact">
          <span>{{ t('app.updated') }}</span
          ><strong>{{ formatDate(pkg.updatedAt, locale) }}</strong>
        </div>
        <div class="fact">
          <span>{{ t('app.source') }}</span
          ><a :href="pkg.repositoryUrl" target="_blank">{{ pkg.repository }}</a>
        </div>
        <div class="fact">
          <span>{{ t('app.upstream') }}</span
          ><a :href="pkg.upstreamUrl" target="_blank">{{ pkg.upstreamRepository }}</a>
        </div>
        <div class="fact">
          <span>{{ t('app.release') }}</span
          ><strong>{{ pkg.releaseTag }}</strong>
        </div>
        <div class="fact">
          <span>{{ t('app.license') }}</span
          ><strong>{{ pkg.license }}</strong>
        </div>
        <div class="fact">
          <span>{{ t('app.packageSource') }}</span
          ><strong>{{
            pkg.sourceType === 'packaged' ? t('app.packageRepository') : t('app.upstreamRelease')
          }}</strong>
        </div>
      </v-card>
    </div>
  </v-container>
  <v-container v-else-if="loading" class="app-shell py-16"
    ><v-progress-linear indeterminate
  /></v-container>
  <v-container v-else class="app-shell text-center py-16"
    ><h2>{{ t('app.noPackage') }}</h2>
    <v-btn to="/" class="mt-4">{{ t('app.back') }}</v-btn></v-container
  >
</template>
