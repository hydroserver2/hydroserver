import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'
import hs from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'

export type RouteGuard = (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) => any | void

/** Guards are executed in the order they appear in this array */
export const guards: RouteGuard[] = [
  // TODO(oauth): re-enable the auth guard once OAuth sign-in is wired
  // end-to-end (see the TODO in `components/account/OAuth.vue`).
  // Blocking protected routes now would strand the user on the Login
  // page with only email/password available — fine on its own, but
  // the UX goal is to ship Google OAuth first. Until then every route
  // loads regardless of session state.
  // (to) => {
  //   if (!to.meta?.hasAuthGuard) return null
  //   if (hs.session?.isAuthenticated) return null
  //   return {
  //     name: 'Login',
  //     query: { next: to.fullPath },
  //   }
  // },

  // hasLoggedOutGuard — the Login page is only useful when the user
  // isn't logged in; once they are, bounce them to the home route
  // (or the route named in `meta.redirectAfterLogin`).
  (to) => {
    if (!to.meta?.hasLoggedOutGuard) return null
    if (!hs.session?.isAuthenticated) return null
    const next =
      (typeof to.query.next === 'string' && to.query.next) ||
      (typeof to.meta.redirectAfterLogin === 'string'
        ? to.meta.redirectAfterLogin
        : 'Home')
    // `next` may be a path (from the auth guard) or a route name.
    return next.startsWith('/') ? { path: next } : { name: next }
  },

  // Shared-link workspace switch. An incoming URL carrying `?ws=<id>`
  // switches the active workspace so recipients of a shared link
  // land in the sender's workspace without stopping at the picker.
  // Covers in-app navigations; the fresh-page-load case is handled
  // synchronously in `main.ts` before `app.mount`.
  (to) => {
    const urlId = typeof to.query.ws === 'string' ? to.query.ws : ''
    if (!urlId) return null
    const ws = useWorkspaceStore()
    if (ws.selectedWorkspaceId === urlId) return null
    ws.applyWorkspaceById(urlId)
    return null
  },

  // Workspaces picker shortcut — if the user already has a selection
  // (typical reload / deep-link case), skip the picker synchronously
  // so it never flashes on the way to the intended page. The nav
  // rail's "Switch workspace" action sets `?switch=1` to opt into
  // showing the picker even with a selection.
  (to) => {
    if (to.name !== 'Workspaces') return null
    if (to.query.switch === '1') return null
    const { hasSelection } = useWorkspaceStore()
    if (!hasSelection) return null
    const next = typeof to.query.next === 'string' ? to.query.next : 'Home'
    return next.startsWith('/') ? { path: next } : { name: next }
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
