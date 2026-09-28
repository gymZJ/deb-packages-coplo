import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import i18n from './i18n/index.js'
import vuetify from './plugins/vuetify.js'
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import './styles/main.css'

createApp(App).use(router).use(vuetify).use(i18n).mount('#app')
