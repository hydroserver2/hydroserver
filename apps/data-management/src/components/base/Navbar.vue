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

    <template v-if="compactNavigation" v-slot:append>
      <v-app-bar-nav-icon
        class="mx-2"
        data-testid="mobile-nav-button"
        @click.stop="drawer = !drawer"
      />
    </template>

    <template v-if="!compactNavigation">
      <div
        v-for="(path, index) of visiblePaths()"
        :key="path.label"
        class="main-nav-item-wrapper"
        :class="{ 'main-nav-item-wrapper--first': index === 0 }"
      >
        <MainNavItem
          :label="path.label"
          :to="path.attrs?.to"
          :href="path.attrs?.href"
          :active="isNavItemActive(path)"
          :on-click="path.onClick"
        />
      </div>

      <v-spacer />

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

          <v-menu bottom left activator="parent">
            <v-list class="pa-0" min-width="200">
              <v-list-item
                :prepend-icon="mdiAccountCircle"
                :to="{ path: '/profile' }"
                data-testid="account-menu-item"
                title="Account"
              />

              <v-list-item
                :prepend-icon="mdiInformation"
                :to="{ path: '/about' }"
                data-testid="about-menu-item"
                title="About"
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
          :href="hs.session.accountSignupUrl"
          >Sign up</v-btn
        >
      </template>
    </template>
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
          to="/about"
          :prepend-icon="mdiInformation"
          data-testid="about-drawer-item"
          >About</v-list-item
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
          :href="hs.session.accountSignupUrl"
          >Sign up</v-list-item
        >
      </template>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { Snackbar } from '@/utils/notifications'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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
  mdiShieldCheckOutline,
  mdiShieldEditOutline,
  mdiTransitConnectionVariant,
} from '@mdi/js'

const route = useRoute()
const { resetState } = useDataVisStore()
const { user } = storeToRefs(useUserStore())
const signupEnabled =
  import.meta.env.VITE_APP_DISABLE_ACCOUNT_CREATION !== 'true'

const sidebar = useSidebarStore()
const drawer = ref(false)
const compactNavigation = ref(false)
let compactNavigationQuery: MediaQueryList | undefined

function updateCompactNavigation() {
  compactNavigation.value = compactNavigationQuery?.matches ?? false
}

onMounted(() => {
  // The full authenticated navigation needs more room than Vuetify's 960px
  // small-screen breakpoint, but comfortably fits below its 1280px medium
  // breakpoint. Collapse at the bar's measured content boundary instead.
  compactNavigationQuery = window.matchMedia('(max-width: 1099px)')
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
// "About" isn't here - when logged in it lives in the account menu instead,
// and is appended back to the end of the bar for logged-out visitors below.
const basePaths: NavItem[] = [
  {
    attrs: { to: '/workspaces' },
    label: 'Manage workspaces',
    icon: mdiBriefcaseOutline,
  },
  {
    attrs: { to: '/browse' },
    label: 'Browse monitoring sites',
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
    label: 'Quality Control',
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

  // Logged-in visitors reach About through the account menu instead.
  if (!authenticated) items.push(aboutPath)

  return items
}

function isNavItemActive(item: NavItem) {
  if (!item.attrs?.to) return false
  const targetPath = router.resolve(item.attrs.to).path
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
.main-nav-item-wrapper--first {
  margin-left: -6px;
}
.account-menu-btn {
  margin-right: var(--hs-space-8);
}
.account-avatar-initials {
  color: #ffffff;
  letter-spacing: 0.02em;
}
</style>
