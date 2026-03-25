import { RouteRecordRaw } from 'vue-router'
import { enableHomePage } from '@/config/homeConfig'
import hs from '@hydroserver/client'

export const routes: RouteRecordRaw[] = [
  enableHomePage
    ? {
        path: '/',
        name: 'Home',
        component: () => import('@/config/Home.vue'),
        meta: { title: 'Home' },
      }
    : {
        path: '/',
        redirect: '/browse',
      },
  {
    path: '/browse',
    name: 'Browse',
    component: () => import('@/pages/Browse.vue'),
    meta: {
      hideFooter: true,
      hasSidebar: true,
      title: 'Browse Monitoring Sites',
      metaTags: [
        {
          name: 'keywords',
          content: 'HydroServer, Site Types, Map, Sites, Data',
        },
      ],
    },
  },
  {
    path: '/sites',
    name: 'Sites',
    component: () => import('@/pages/Sites.vue'),
    meta: {
      requiresAuth: true,
      title: 'Your Sites',
      metaTags: [
        {
          name: 'keywords',
          content: 'HydroServer, Your Sites',
        },
      ],
    },
  },
  {
    path: '/sites/:id',
    name: 'SiteDetails',
    component: () => import('@/pages/SiteDetails.vue'),
    meta: {
      title: 'Site',
      metaTags: [
        {
          name: 'keywords',
          content: 'HydroServer, Site',
        },
      ],
    },
  },
  {
    path: '/about',
    name: 'Contact',
    component: () => import('@/pages/About.vue'),
    meta: {
      title: 'About',
      metaTags: [
        {
          name: 'keywords',
          content: 'HydroServer, About, GitHub, Email',
        },
      ],
    },
  },
  {
    path: '/orchestration',
    name: 'Orchestration',
    component: () => import('@/pages/Orchestration.vue'),
    meta: { requiresAuth: true, hideFooter: true },
  },
  {
    path: '/hydroloader/download',
    name: 'HydroLoader',
    component: () => import('@/pages/HydroLoaderDownload.vue'),
  },
  {
    path: '/callback',
    name: 'Callback',
    component: () => import('@/pages/Callback.vue'),
    meta: {
      title: 'Signing In',
      hideNavBar: true,
      hideFooter: true,
    },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/pages/Redirecting.vue'),
    beforeEnter: () => {
      window.location.assign(hs.session.accountProfileUrl)
      return false
    },
    meta: { requiresAuth: true, title: 'Profile' },
  },
  {
    path: '/metadata',
    name: 'Metadata',
    component: () => import('@/pages/Metadata.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/access-denied',
    name: 'AccessDenied',
    component: () => import('@/pages/AccessDenied.vue'),
    meta: { requiresAuth: true, title: 'Access Denied' },
  },
  {
    path: '/visualize-data/:thingId?',
    name: 'VisualizeData',
    component: () => import('@/pages/VisualizeData.vue'),
    meta: {
      title: 'VisualizeData',
      hasSidebar: true,
      hideFooter: true,
      metaTags: [
        {
          name: 'keywords',
          content: 'HydroServer, Data Visualization',
        },
      ],
    },
  },
  {
    path: '/:catchAll(.*)*',
    name: 'PageNotFound',
    component: () => import('@/pages/PageNotFound.vue'),
    meta: { title: 'Page Not Found' },
  },
]
