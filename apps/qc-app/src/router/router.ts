import { routes } from '@/router/routes'
import { createRouter, createWebHistory } from 'vue-router'
import { guards } from '@/router/guards'

const router = createRouter({
  history: createWebHistory('/qc/'),
  routes,
})

export function setupRouteGuards() {
  // Return the guard's result rather than calling `next()` — the callback
  // form is deprecated in vue-router. `false` cancels, a route location
  // redirects, and null/undefined proceeds to the next guard.
  guards.forEach((fn) => {
    router.beforeEach(async (to, from) => {
      const result = await fn(to, from)
      if (result === false) return false
      if (result === null || result === undefined) return true
      return result
    })
  })
}

export default router
