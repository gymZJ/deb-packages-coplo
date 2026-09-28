import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import PackageDetailView from '../views/PackageDetailView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/packages/:name', component: PackageDetailView },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
