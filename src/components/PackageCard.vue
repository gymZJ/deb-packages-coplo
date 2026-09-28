<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate, formatSize } from '../utils/format.js'

const props = defineProps({ pkg: { type: Object, required: true } })
const { locale, t } = useI18n()
const artifact = computed(() => props.pkg.architectures[0])
</script>

<template>
  <v-card :to="`/packages/${pkg.id}`" border class="mobile-package-card">
    <div class="mobile-card-head">
      <div class="mobile-title">
        <strong>{{ pkg.name }}</strong>
        <code>{{ pkg.version }}</code>
      </div>
      <v-icon icon="mdi-chevron-right" size="18" />
    </div>
    <div class="mobile-meta-grid">
      <div>
        <span>{{ t('app.source') }}</span
        ><strong>{{ pkg.repository }}</strong>
      </div>
      <div>
        <span>{{ t('app.updated') }}</span
        ><strong>{{ formatDate(pkg.updatedAt, locale) }}</strong>
      </div>
      <div>
        <span>{{ t('app.size') }}</span
        ><strong>{{ formatSize(artifact?.size) }}</strong>
      </div>
    </div>
  </v-card>
</template>
