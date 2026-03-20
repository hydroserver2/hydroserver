import {
  RouteLocationNormalized,
  RouteRecordNormalized,
  createRouter,
  createWebHistory,
} from 'vue-router'
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
  async (to: RouteLocationNormalized, from: RouteLocationNormalized) => {
    const { inEmailVerificationFlow, inProviderSignupFlow } = hs.session

    if (inEmailVerificationFlow && to.name !== 'VerifyEmail') {
      if (to.name === 'ResetPassword') return { name: 'ResetPassword' }
      return { name: 'VerifyEmail' }
    }
    if (!inEmailVerificationFlow && to.name === 'VerifyEmail')
      return { name: 'Sites' }

    if (inProviderSignupFlow && to.name !== 'CompleteProfile')
      return { name: 'CompleteProfile' }
    if (!inProviderSignupFlow && to.name === 'CompleteProfile')
      return { name: 'Sites' }

    if (hs.session.isAuthenticated && to.meta.requiresLoggedOut)
      return { name: 'Sites' }
    if (!hs.session.isAuthenticated && to.meta.requiresAuth)
      return { name: 'Login', query: { next: to.fullPath } }
  }
)

router.afterEach(
  (to: RouteLocationNormalized, from: RouteLocationNormalized) => {
    updateDocumentTitle(to.matched)
  }
)

export default router
