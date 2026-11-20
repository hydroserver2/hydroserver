<template>
  <v-app-bar app :elevation="0" class="navbar-flat" density="default">
    <template
      v-slot:prepend
      v-if="route.meta.hasSidebar && route.name !== 'VisualizeData'"
    >
      <v-app-bar-nav-icon
        v-if="sidebar.isOpen"
        :icon="mdiMenuOpen"
        @click.stop="sidebar.toggle"
        class="mx-3"
        variant="tonal"
        rounded="lg"
        size="large"
      />
      <v-app-bar-nav-icon
        v-else
        :icon="mdiMenuClose"
        @click.stop="sidebar.toggle"
        class="mx-3"
        variant="tonal"
        rounded="lg"
        size="large"
      />
    </template>
    <router-link
      v-if="navbarLogo.route"
      :to="navbarLogo.route"
      class="navbar-home-link"
    >
      <v-img :src="navbarLogo.src" alt="Logo" width="146" height="62" />
    </router-link>
    <a
      v-else-if="navbarLogo.link"
      :href="navbarLogo.link"
      :target="navbarLogo.target || '_self'"
      class="navbar-home-link"
    >
      <v-img :src="navbarLogo.src" alt="Logo" width="146" height="62" />
    </a>

    <v-app-bar-nav-icon
      v-if="compactNavigation"
      class="compact-nav-toggle mx-2"
      data-testid="mobile-nav-button"
      aria-label="Toggle navigation menu"
      :aria-expanded="drawer"
      @click.stop="drawer = !drawer"
    />

    <div
      class="navbar-desktop"
      :class="{ 'navbar-desktop--compact': compactNavigation }"
      :inert="compactNavigation ? true : undefined"
      :aria-hidden="compactNavigation ? true : undefined"
    >
      <div ref="navigationContainer" class="main-navigation">
        <div ref="navigationLinks" class="main-navigation-links">
          <div
            v-for="(path, index) of visiblePaths()"
            :key="path.label"
            class="main-nav-item-wrapper"
            :class="{
              'main-nav-item-wrapper--first': index === 0,
              'main-nav-item-wrapper--overflow':
                path === aboutPath && aboutInMenu,
            }"
            :inert="path === aboutPath && aboutInMenu ? true : undefined"
            :aria-hidden="path === aboutPath && aboutInMenu ? true : undefined"
          >
            <MainNavItem
              :label="path.label"
              :to="path.attrs?.to"
              :href="path.attrs?.href"
              :active="isNavItemActive(path)"
              :on-click="path.onClick"
            />
          </div>
        </div>
      </div>

      <template v-if="hs.session.isAuthenticated">
        <v-btn
          data-testid="account-menu-button"
          icon
          size="40"
          class="account-menu-btn"
        >
          <v-avatar color="primary" size="36">
            <span class="account-avatar-initials hs-title">{{
              userInitials
            }}</span>
          </v-avatar>

          <v-menu v-if="!compactNavigation" bottom left activator="parent">
            <v-list class="pa-0" min-width="200">
              <v-list-item
                :prepend-icon="mdiAccountCircle"
                :to="{ path: '/profile' }"
                data-testid="account-menu-item"
                title="Account"
              />

              <v-list-item
                v-if="aboutInMenu"
                :prepend-icon="mdiInformation"
                :to="{ path: '/about' }"
                data-testid="about-menu-item"
                title="About"
              />

              <v-list-item
                v-if="user.isStaff"
                :prepend-icon="mdiViewDashboardOutline"
                :href="adminDashboardUrl"
                data-testid="admin-menu-item"
                title="Admin dashboard"
              />

              <v-divider />

              <v-list-item
                :prepend-icon="mdiLogout"
                @click="onLogout"
                data-testid="logout-menu-item"
                title="Log out"
              />
            </v-list>
          </v-menu>
        </v-btn>
      </template>

      <template v-else>
        <v-btn :prepend-icon="mdiLogin" @click="onLogin">Log in</v-btn>
        <v-btn
          v-if="signupEnabled"
          :prepend-icon="mdiAccountPlusOutline"
          :href="hs.session.getAccountSignupUrl()"
          >Sign up</v-btn
        >
      </template>
    </div>
  </v-app-bar>

  <v-navigation-drawer
    v-if="compactNavigation"
    temporary
    v-model="drawer"
    location="right"
  >
    <v-list density="compact" nav>
      <div v-for="path of visiblePaths()" :key="path.label">
        <v-list-item
          v-bind="path.attrs || {}"
          :data-testid="path === aboutPath ? 'about-drawer-item' : undefined"
          :title="path.label"
          :prepend-icon="path.icon"
          :value="path.attrs?.to || path.attrs?.href || path.label"
          @click="path.onClick"
        />
      </div>
    </v-list>

    <v-divider />

    <v-list density="compact" nav>
      <template v-if="hs.session.isAuthenticated">
        <v-list-item
          to="/profile"
          :prepend-icon="mdiAccountCircle"
          data-testid="account-drawer-item"
          >Account</v-list-item
        >
        <v-list-item
          v-if="user.isStaff"
          :href="adminDashboardUrl"
          :prepend-icon="mdiViewDashboardOutline"
          data-testid="admin-drawer-item"
          >Admin dashboard</v-list-item
        >
        <v-list-item
          :prepend-icon="mdiLogout"
          @click.prevent="onLogout"
          data-testid="logout-drawer-item"
          >Logout</v-list-item
        >
      </template>

      <template v-else>
        <v-list-item :prepend-icon="mdiLogin" @click.prevent="onLogin"
          >Login</v-list-item
        >
        <v-list-item
          v-if="signupEnabled"
          :prepend-icon="mdiAccountPlusOutline"
          :href="hs.session.getAccountSignupUrl()"
          >Sign up</v-list-item
        >
      </template>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { Snackbar } from '@/utils/notifications'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { useUserStore } from '@/store/user'
import { navbarLogo } from '@/config/navbarConfig'
import MainNavItem from '@/components/base/MainNavItem.vue'
import { RouteLocationRaw, useRoute } from 'vue-router'
import { useSidebarStore } from '@/store/useSidebar'
import hs from '@hydroserver/client'
import router from '@/router/router'
import {
  mdiAccountCircle,
  mdiAccountPlusOutline,
  mdiBriefcaseOutline,
  mdiChartLine,
  mdiInformation,
  mdiLogin,
  mdiLogout,
  mdiMapMarkerOutline,
  mdiMenuClose,
  mdiMenuOpen,
  mdiShieldEditOutline,
  mdiTransitConnectionVariant,
  mdiViewDashboardOutline,
} from '@mdi/js'

const route = useRoute()
const { resetState } = useDataVisStore()
const { user } = storeToRefs(useUserStore())
const signupEnabled =
  import.meta.env.VITE_APP_DISABLE_ACCOUNT_CREATION !== 'true'
const adminDashboardUrl = hs.resolveUrl('/admin/')

const sidebar = useSidebarStore()
const drawer = ref(false)
const smallScreen = ref(false)
const mainLinksOverflow = ref(false)
const compactNavigation = computed(
  () => smallScreen.value || mainLinksOverflow.value
)
const navigationContainer = ref<HTMLElement>()
const navigationLinks = ref<HTMLElement>()
const aboutInMenu = ref(false)
let compactNavigationQuery: MediaQueryList | undefined

watch(
  [navigationContainer, navigationLinks],
  ([container, links], _, onCleanup) => {
    if (!container || !links) return

    const updateAboutOverflow = () => {
      // Keep About's space measurable while it is hidden so growing the bar
      // restores the link without oscillating between the bar and menu.
      const availableWidth = container.getBoundingClientRect().width
      const requiredWidth = links.getBoundingClientRect().width
      const aboutWidth =
        links.lastElementChild?.getBoundingClientRect().width ?? 0
      aboutInMenu.value =
        hs.session.isAuthenticated && requiredWidth > availableWidth
      // Guests have no account menu, so keep About with the other links when
      // deciding whether the full navigation needs to move into the drawer.
      mainLinksOverflow.value =
        requiredWidth - (hs.session.isAuthenticated ? aboutWidth : 0) >
        availableWidth
    }
    const observer = new ResizeObserver(updateAboutOverflow)
    observer.observe(container)
    observer.observe(links)
    updateAboutOverflow()
    onCleanup(() => observer.disconnect())
  },
  { flush: 'post' }
)

function updateCompactNavigation() {
  smallScreen.value = compactNavigationQuery?.matches ?? false
}

onMounted(() => {
  // The shorter labels let the main links stay in the bar down to Vuetify's
  // small-screen breakpoint; About overflows into the account menu first.
  compactNavigationQuery = window.matchMedia('(max-width: 959px)')
  updateCompactNavigation()
  compactNavigationQuery.addEventListener('change', updateCompactNavigation)
})

onBeforeUnmount(() => {
  compactNavigationQuery?.removeEventListener('change', updateCompactNavigation)
})

const userInitials = computed(() => {
  const first = user.value.firstName?.trim()?.[0] ?? ''
  const last = user.value.lastName?.trim()?.[0] ?? ''
  return (first + last).toUpperCase()
})

type NavItemAttrs = {
  to?: RouteLocationRaw
  href?: string
}

type NavItem = {
  attrs?: NavItemAttrs
  label: string
  icon?: string
  onClick?: () => void
  requiresAuth?: boolean
}

// The base nav items, before filtering out anything that requires a login.
const basePaths: NavItem[] = [
  {
    attrs: { to: '/workspaces' },
    label: 'Workspaces',
    icon: mdiBriefcaseOutline,
  },
  {
    attrs: { to: '/browse' },
    label: 'Monitoring Sites',
    icon: mdiMapMarkerOutline,
  },
  {
    attrs: { to: '/visualize-data' },
    label: 'Visualize data',
    icon: mdiChartLine,
    onClick: () => resetState(),
  },
  {
    // Points straight at the redirect's target rather than '/orchestration'
    // itself - router.resolve() doesn't inherit a redirect target's meta, so
    // requiresAuth filtering needs the real route here to work.
    attrs: { to: '/orchestration/ingestion' },
    label: 'Job orchestration',
    icon: mdiTransitConnectionVariant,
  },
  {
    label: 'Quality control',
    icon: mdiShieldEditOutline,
    requiresAuth: true,
    onClick: () => {
      window.location.href = '/qc/'
    },
  },
]

const aboutPath: NavItem = {
  attrs: { to: '/about' },
  label: 'About',
  icon: mdiInformation,
}

/** Whether a nav item's target route requires the visitor to be logged in. */
function itemRequiresAuth(attrs?: NavItemAttrs): boolean {
  if (!attrs?.to) return false
  return !!router.resolve(attrs.to).meta?.requiresAuth
}

// Recomputed on every render (rather than a cached computed) so it stays in
// sync with hs.session.isAuthenticated the same way the rest of this
// component's auth-gated markup does.
function visiblePaths(): NavItem[] {
  const authenticated = hs.session.isAuthenticated
  const items = basePaths.filter(
    (item) =>
      authenticated || !(item.requiresAuth || itemRequiresAuth(item.attrs))
  )

  items.push(aboutPath)

  return items
}

function isNavItemActive(item: NavItem) {
  if (!item.attrs?.to) return false
  const targetPath = router.resolve(item.attrs.to).path

  // The orchestration nav target points to the default tab, but every
  // orchestration tab and task-detail route belongs to the same main-nav item.
  if (
    targetPath === '/orchestration/ingestion' &&
    route.path.startsWith('/orchestration/')
  ) {
    return true
  }

  return route.path === targetPath || route.path.startsWith(`${targetPath}/`)
}

async function onLogin() {
  await hs.session.login(route.fullPath)
}

async function onLogout() {
  await hs.session.logout('/browse')
  Snackbar.info('You have logged out')
}
</script>

<style scoped>
.v-app-bar.navbar-flat,
:deep(.v-app-bar.navbar-flat) {
  background: var(--hs-surface) !important;
  border-bottom: 1px solid var(--hs-border) !important;
  box-shadow: none !important;
}
.navbar-home-link {
  flex-shrink: 0;
  width: 160px;
  height: 64px;
  margin: 0 0 0 4px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  line-height: 0;
}
.main-navigation {
  flex: 1;
  min-width: 0;
  align-self: stretch;
  overflow: hidden;
}
.navbar-desktop {
  display: flex;
  flex: 1;
  min-width: 0;
  align-self: stretch;
  align-items: center;
}
.navbar-desktop--compact {
  /* Preserve the link measurements while the drawer is in use. */
  visibility: hidden;
}
.compact-nav-toggle {
  position: absolute;
  right: 0;
}
.main-navigation-links {
  display: flex;
  width: max-content;
  height: 100%;
}
.main-nav-item-wrapper--first {
  margin-left: calc(-1 * var(--hs-space-6));
}
.main-nav-item-wrapper--overflow {
  visibility: hidden;
}
.account-menu-btn {
  margin-right: var(--hs-space-8);
}
.account-avatar-initials {
  color: #ffffff;
  letter-spacing: 0.02em;
}
</style>
