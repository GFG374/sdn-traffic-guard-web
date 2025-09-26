import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../components/Login.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../components/ForgotPassword.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('../components/ResetPassword.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('../components/ChangePassword.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/account-details',
    name: 'AccountDetails',
    component: () => import('../components/AccountDetails.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../components/Dashboard/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/anomalies',
    name: 'Anomalies',
    component: () => import('../components/Anomalies/Anomalies.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ratelimit',
    name: 'RateLimit',
    component: () => import('../components/RateLimit/RateLimit.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/acl',
    name: 'ACL',
    component: () => import('../components/ACL/ACL.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/flowstats',
    name: 'FlowStats',
    component: () => import('../components/FlowStats/FlowStats.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ai-assistant',
    name: 'AIAssistant',
    component: () => import('../components/AIAssistant/AIAssistant.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.requiresGuest && userStore.isAuthenticated) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router