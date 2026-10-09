import { routes } from '@/router/routes'
import { createRouter, createWebHistory } from 'vue-router'
import { guards, updateHead } from '@/router/guards'
import { isLeavingPage } from '@/router/navigationState'

const router = createRouter({
  history: createWebHistory('/qc/'),
  routes,
})

export function setupRouteGuards() {
  // `false` cancels, a location redirects, and null/undefined continues.
  guards.forEach((fn) => {
    router.beforeEach(async (to, from) => {
      const result = await fn(to, from)
      if (result === false) return false
      if (result === null || result === undefined) return true
      return result
    })
  })
  router.afterEach((to, from, failure) => {
    // The leave guard's navigation has landed or been cancelled.
    isLeavingPage.value = false
    if (!failure) updateHead(to, from)
  })
}

export default router
