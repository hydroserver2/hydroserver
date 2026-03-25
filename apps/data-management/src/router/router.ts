import {
  RouteLocationNormalized,
  RouteRecordNormalized,
  createRouter,
  createWebHistory,
} from 'vue-router'
import {
  isHydroServerReady,
  waitForHydroServerInitialization,
} from '@/bootstrap/appInitialization'
import { routes } from '@/router/routes'
import hs from '@hydroserver/client'

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * Updates the document title based on the nearest route with a title meta field.
 */
function updateDocumentTitle(matched: RouteRecordNormalized[]): void {
  const nearestWithTitle = matched
    .slice()
    .reverse()
    .find((route) => route.meta && route.meta.title)

  if (nearestWithTitle) {
    document.title = `HydroServer | ${nearestWithTitle.meta.title}`
  } else {
    document.title = 'HydroServer'
  }
}

router.beforeEach(
  async (to: RouteLocationNormalized) => {
    await waitForHydroServerInitialization()
    if (!isHydroServerReady.value) return false

    if (!hs.session.isAuthenticated && to.meta.requiresAuth) {
      await hs.session.login(to.fullPath)
      return false
    }
  }
)

router.afterEach((to: RouteLocationNormalized) => {
  updateDocumentTitle(to.matched)
})

export default router
