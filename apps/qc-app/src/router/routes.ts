import type { RouteRecordRaw } from 'vue-router';

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
    meta: {
      hasAuthGuard: true,
      hasWorkspaceGuard: true,
      title: 'Home',
      hasRibbon: true,
    },
  },
  {
    path: '/workspaces',
    name: 'Workspaces',
    component: () => import('@/pages/Workspaces.vue'),
    meta: {
      hasAuthGuard: true,
      title: 'Workspaces',
    },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/account/Login.vue'),
    meta: {
      title: 'Login',
      hasLoggedOutGuard: true,
      redirectAfterLogin: 'Home',
      disablePasswordReset: true,
    },
  },
]
