import { routes } from '@/router/routes'
import { createRouter, createWebHistory } from 'vue-router'
import { guards } from '@/router/guards'

const base = import.meta.env.VITE_APP_ROUTE || '/'

const router = createRouter({
  history: createWebHistory(base),
  routes,
})

export function setupRouteGuards() {
  guards.map((fn) => {
    router.beforeEach(async (to, from, next) => {
      const activatedRouteGuard = await fn(to, from, next)
      if (activatedRouteGuard) {
        next(activatedRouteGuard)
      } else {
        next()
      }
    })
  })
}

export default router
