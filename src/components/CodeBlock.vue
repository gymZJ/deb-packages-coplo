<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({ code: { type: String, required: true } })
const { t } = useI18n()
const copied = ref(false)

async function copyText() {
  await navigator.clipboard.writeText(props.code)
  copied.value = true
  window.setTimeout(() => {
    copied.value = false
  }, 1400)
}
</script>

<template>
  <div class="code-block">
    <pre><code>{{ code }}</code></pre>
    <v-tooltip :text="copied ? t('app.copied') : t('app.copy')">
      <template #activator="{ props: activatorProps }">
        <v-btn
          v-bind="activatorProps"
          class="copy-btn"
          size="small"
          variant="text"
          :icon="copied ? 'mdi-check' : 'mdi-content-copy'"
          @click="copyText"
        />
      </template>
    </v-tooltip>
  </div>
</template>
