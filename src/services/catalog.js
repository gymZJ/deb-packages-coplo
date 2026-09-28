import { readonly, ref } from 'vue'
import { repository } from '../config/repository.js'

const packages = ref([])
const suites = ref([])
const defaultSuite = ref('')
const loading = ref(false)
const error = ref(null)
let loaded = false

function mapSuite(item) {
  if (typeof item === 'string') {
    return { value: item, label: item, default: false }
  }
  return {
    value: item.name,
    label: item.label || item.name,
    default: Boolean(item.default),
  }
}

function mapPackage(item) {
  const artifacts = (item.artifacts || []).map((artifact) => ({
    package: artifact.package || item.name,
    version: artifact.version || item.version || '—',
    name: artifact.architecture,
    filename: artifact.filename || artifact.url.split('/').pop() || artifact.architecture,
    suites: artifact.suites || [],
    size: Number(artifact.size),
    url: artifact.url,
    sha256: artifact.sha256,
  }))

  return {
    id: item.name,
    name: item.name,
    version: item.version || '—',
    repository: item.repository,
    repositoryUrl: item.repository_url,
    upstreamRepository: item.upstream_repository,
    upstreamUrl: item.upstream_url,
    sourceType: item.source_type,
    releaseTag: item.release_tag,
    license: item.license || '—',
    updatedAt: item.updated_at,
    artifacts,
    architectures: artifacts,
  }
}

export async function loadCatalog({ force = false } = {}) {
  if (loaded && !force) return packages.value
  loading.value = true
  error.value = null
  try {
    const response = await fetch(repository.catalogUrl, { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const catalog = await response.json()
    suites.value = (catalog.suites || []).map(mapSuite)
    defaultSuite.value =
      suites.value.find((suite) => suite.default)?.value || suites.value[0]?.value || ''
    packages.value = (catalog.packages || []).map(mapPackage)
    loaded = true
    return packages.value
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
    throw cause
  } finally {
    loading.value = false
  }
}

export function useCatalog() {
  return {
    packages: readonly(packages),
    suites: readonly(suites),
    defaultSuite: readonly(defaultSuite),
    loading: readonly(loading),
    error: readonly(error),
    loadCatalog,
  }
}
