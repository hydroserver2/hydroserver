<template>
  <v-app-bar app elevation="2" density="default">
    <template
      v-slot:prepend
      v-if="route.meta.hasSidebar && route.name !== 'VisualizeData'"
    >
      <v-app-bar-nav-icon
        v-if="sidebar.isOpen"
        :icon="mdiMenuOpen"
        @click="sidebar.toggle"
        class="mx-3"
        variant="tonal"
        rounded="lg"
        size="large"
      />
      <v-app-bar-nav-icon
        v-else
        :icon="mdiMenuClose"
        @click="sidebar.toggle"
        class="mx-3"
        variant="tonal"
        rounded="lg"
        size="large"
      />
    </template>
    <router-link v-if="navbarLogo.route" :to="navbarLogo.route">
      <v-img :src="navbarLogo.src" alt="Logo" :width="navbarLogo.width" />
    </router-link>
    <a
      v-else-if="navbarLogo.link"
      :href="navbarLogo.link"
      :target="navbarLogo.target || '_self'"
    >
      <v-img :src="navbarLogo.src" alt="Logo" :width="navbarLogo.width" />
    </a>

    <template v-if="mdAndDown" v-slot:append>
      <v-app-bar-nav-icon class="mx-2" @click.stop="drawer = !drawer" />
    </template>

    <template v-if="!mdAndDown">
      <div v-for="path of paths" :key="path.label">
        <v-btn
          v-if="!path.menu"
          v-bind="path.attrs"
          @click="path.onClick"
          density="comfortable"
        >
          {{ path.label }}
        </v-btn>

        <v-menu v-else>
          <template v-slot:activator="{ props }">
            <v-btn v-bind="props">
              {{ path.label }}
              <v-icon :icon="mdiMenuDown" right small />
            </v-btn>
          </template>

          <v-list>
            <v-list-item
              v-for="menuItem of path.menu"
              v-bind="menuItem.attrs"
              :title="menuItem.label"
            />
          </v-list>
        </v-menu>
      </div>

      <v-spacer />

      <template v-if="isHydroServerAuthenticated">
        <v-btn data-testid="account-menu-button" elevation="2" rounded>
          <v-icon :icon="mdiAccountCircle" />
          <v-icon :icon="mdiMenuDown" />

          <v-menu bottom left activator="parent">
            <v-list class="pa-0">
              <v-list-item
                :prepend-icon="mdiAccountCircle"
                :to="{ path: '/profile' }"
                data-testid="account-menu-item"
                title="Account"
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
    v-if="mdAndDown"
    temporary
    v-model="drawer"
    location="right"
  >
    <v-list density="compact" nav>
      <div v-for="path of paths">
        <v-list-item
          v-if="path.attrs"
          v-bind="path.attrs"
          :title="path.label"
          :prepend-icon="path.icon"
          :value="path.attrs.to || path.attrs.href"
          @click="path.onClick"
        />
        <div v-else>
          <v-list-item
            v-for="menuItem of path.menu"
            v-bind="menuItem.attrs"
            :title="menuItem.label"
            :prepend-icon="menuItem.icon"
            :value="menuItem.attrs.to || menuItem.attrs.href"
          />
        </div>
      </div>
    </v-list>

    <v-divider />

    <v-list density="compact" nav>
      <template v-if="isHydroServerAuthenticated">
        <v-list-item
          to="/profile"
          :prepend-icon="mdiAccountCircle"
          data-testid="account-drawer-item"
          >Account</v-list-item
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
import { useDisplay } from 'vuetify/lib/framework.mjs'
import { isHydroServerAuthenticated } from '@/bootstrap/appInitialization'
import { Snackbar } from '@/utils/notifications'
import { ref } from 'vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { navbarLogo } from '@/config/navbarConfig'
import { useRoute } from 'vue-router'
import { useSidebarStore } from '@/store/useSidebar'
import hs from '@hydroserver/client'
import router from '@/router/router'
import {
  mdiAccountCircle,
  mdiAccountPlusOutline,
  mdiChartLine,
  mdiDatabaseCog,
  mdiFileChart,
  mdiInformation,
  mdiLayersSearch,
  mdiLogin,
  mdiLogout,
  mdiMapMarkerMultiple,
  mdiMenuClose,
  mdiMenuDown,
  mdiMenuOpen,
} from '@mdi/js'

const route = useRoute()
const { resetState } = useDataVisStore()
const { mdAndDown } = useDisplay()
const signupEnabled = import.meta.env.VITE_APP_DISABLE_ACCOUNT_CREATION !== 'true'

const sidebar = useSidebarStore()
const drawer = ref(false)

const paths: {
  attrs?: { to?: string; href?: string }
  label: string
  icon?: string
  menu?: any[]
  onClick?: () => void
}[] = [
  {
    attrs: { to: '/browse' },
    label: 'Browse monitoring sites',
    icon: mdiLayersSearch,
  },
  {
    attrs: { to: '/sites' },
    label: 'Your sites',
    icon: mdiMapMarkerMultiple,
  },
  {
    attrs: { to: '/visualize-data' },
    label: 'Visualize data',
    icon: mdiChartLine,
    onClick: () => resetState(),
  },
  {
    label: 'Data management',
    menu: [
      {
        attrs: { to: '/Metadata' },
        label: 'Manage metadata',
        icon: mdiDatabaseCog,
      },
      {
        attrs: { to: '/orchestration' },
        label: 'Job orchestration',
        icon: mdiFileChart,
      },
    ],
  },
  {
    attrs: { to: '/about' },
    label: 'About',
    icon: mdiInformation,
  },
]

async function onLogin() {
  await hs.session.login(route.fullPath)
}

async function onLogout() {
  await hs.session.logout('/browse')
  Snackbar.info('You have logged out')
}
</script>
