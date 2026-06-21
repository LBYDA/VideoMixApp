import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/category-mix',
      name: 'category-mix',
      component: () => import('@/views/CategoryMixView.vue'),
    },
    {
      path: '/ai-mix',
      name: 'ai-mix',
      component: () => import('@/views/AiMixView.vue'),
    },
    {
      path: '/video-mix',
      name: 'video-mix',
      component: () => import('@/views/VideoMixView.vue'),
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: () => import('@/views/JobHistoryView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
    },
  ],
})

export default router
