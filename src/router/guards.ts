import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'
import { storeToRefs } from 'pinia'
import { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'

export type RouteGuard = (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) => any | void

/** Guards are executed in the order they appear in this array */
export const guards: RouteGuard[] = [
  // Check if the refresh token is expired each page change
  // (_to, _from, _next) => {
  //   const { isRefreshTokenExpired, logout } = useAuthStore()

  //   if (isRefreshTokenExpired()) {
  //     Snackbar.info('Session expired. Please login')
  //     logout()
  //   }
  //   return null
  // },

  // hasAuthGuard
  // (to, _from, _next) => {
  //   if (to.meta?.hasAuthGuard) {
  //     const { isLoggedIn } = storeToRefs(useAuthStore())
  //     const { user } = storeToRefs(useUserStore())

  //     if (!isLoggedIn.value) return { name: 'Login', query: { next: to.name } }
  //     if (user.value?.isVerified) return null
  //     if (user.value?.email) return { name: 'VerifyEmail' }
  //     return { name: 'CompleteProfile' }
  //   }
  //   return null
  // },

  // // hasLoggedOutGuard
  // (to, _from, _next) => {
  //   if (to.meta?.hasLoggedOutGuard) {
  //     const { isLoggedIn } = useAuthStore()
  //     if (isLoggedIn) return { name: 'PageNotFound' }
  //   }
  //   return null
  // },

  // // hasUnverifiedAuthGuard
  // (to, _from, _next) => {
  //   if (to.meta?.hasUnverifiedAuthGuard) {
  //     const { isLoggedIn } = useAuthStore()
  //     const { user } = storeToRefs(useUserStore())
  //     if (isLoggedIn && user.value?.isVerified) return { name: 'PageNotFound' }
  //   }
  //   return null
  // },

  // hasThingOwnershipGuard
  async (to, _from, _next) => {
    const { hs } = storeToRefs(useHydroServer())
    if (to.meta?.hasThingOwnershipGuard) {
      const thing = (await hs.value.things.get(to.params.id as string)).data
      // TODO: where to find `ownsThing` property
      // if (!thing?.ownsThing) return { name: 'PageNotFound' }
    }
    return null
  },

  // hasWorkspaceGuard — every data-bearing route needs an active
  // HydroServer workspace context. If none is selected, bounce to the
  // picker and carry a `next` hint so we can come back here once the
  // user commits to a workspace.
  (to, _from, _next) => {
    if (!to.meta?.hasWorkspaceGuard) return null
    const { hasSelection } = useWorkspaceStore()
    if (hasSelection) return null
    return {
      name: 'Workspaces',
      query: { next: typeof to.name === 'string' ? to.name : 'Home' },
    }
  },

  // https://www.digitalocean.com/community/tutorials/vuejs-vue-router-modify-head
  // Append head tags and update page title
  (to, from, _next) => {
    // This goes through the matched routes from last to first, finding the closest route with a title.
    // e.g., if we have `/some/deep/nested/route` and `/some`, `/deep`, and `/nested` have titles,
    // `/nested`'s will be chosen.
    const nearestWithTitle = to.matched
      .slice()
      .reverse()
      .find((r) => r.meta && r.meta.title)

    // Find the nearest route element with meta tags.
    const nearestWithMeta = to.matched
      .slice()
      .reverse()
      .find((r) => r.meta && r.meta.metaTags)

    const previousNearestWithMeta = from?.matched
      .slice()
      .reverse()
      .find((r) => r.meta && r.meta.metaTags)

    // If a route with a title was found, set the document (page) title to that value.
    if (nearestWithTitle) {
      document.title = `HydroServer | ${nearestWithTitle.meta.title}`
    } else if (previousNearestWithMeta) {
      document.title = previousNearestWithMeta.meta.title as string
    } else {
      document.title = `HydroServer`
    }

    // Remove any stale meta tags from the document using the key attribute we set below.
    Array.from(document.querySelectorAll('[data-vue-router-controlled]')).map(
      (el) => el.parentNode?.removeChild(el)
    )

    // Skip rendering meta tags if there are none.
    if (!nearestWithMeta) return null

    // Turn the meta tag definitions into actual elements in the head.
    // @ts-ignore
    nearestWithMeta.meta.metaTags
      .map((tagDef: any) => {
        const tag = document.createElement('meta')

        Object.keys(tagDef).forEach((key) => {
          tag.setAttribute(key, tagDef[key])
        })

        // We use this to track which meta tags we create so we don't interfere with other ones.
        tag.setAttribute('data-vue-router-controlled', '')

        return tag
      })
      // Add the meta tags to the document head.
      .forEach((tag: any) => document.head.appendChild(tag))

    return null
  },
]
