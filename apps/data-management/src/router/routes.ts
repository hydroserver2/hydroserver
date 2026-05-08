import { RouteRecordRaw } from 'vue-router'
import { enableHomePage } from '@/config/homeConfig'

const disableAccountCreation =
  import.meta.env.VITE_APP_DISABLE_ACCOUNT_CREATION || 'false'

const validOrchestrationViews = new Set([
  'ingestion',
  'aggregation',
  'quality',
  'workspaces',
])

const orchestrationComponent = () => import('@/pages/Orchestration.vue')

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
    redirect: '/orchestration/ingestion',
  },
  {
    path: '/orchestration/ingestion/details/ingestion',
    name: 'OrchestrationIngestionDetails',
    component: orchestrationComponent,
    meta: {
      requiresAuth: true,
      hideFooter: true,
      orchestrationView: 'ingestion',
      orchestrationTaskDetail: 'ingestion',
    },
  },
  {
    path: '/orchestration/aggregation/details/aggregation',
    name: 'OrchestrationAggregationDetails',
    component: orchestrationComponent,
    meta: {
      requiresAuth: true,
      hideFooter: true,
      orchestrationView: 'aggregation',
      orchestrationTaskDetail: 'aggregation',
    },
  },
  {
    path: '/orchestration/aggregation/details/expression',
    name: 'OrchestrationExpressionDetails',
    component: orchestrationComponent,
    meta: {
      requiresAuth: true,
      hideFooter: true,
      orchestrationView: 'aggregation',
      orchestrationTaskDetail: 'expression',
    },
  },
  {
    path: '/orchestration/aggregation/details/derivation',
    name: 'OrchestrationDerivationDetails',
    component: orchestrationComponent,
    meta: {
      requiresAuth: true,
      hideFooter: true,
      orchestrationView: 'aggregation',
      orchestrationTaskDetail: 'derivation',
    },
  },
  {
    path: '/orchestration/aggregation/details/rating-curve',
    name: 'OrchestrationRatingCurveDetails',
    component: orchestrationComponent,
    meta: {
      requiresAuth: true,
      hideFooter: true,
      orchestrationView: 'aggregation',
      orchestrationTaskDetail: 'rating-curve',
    },
  },
  {
    path: '/orchestration/quality/details/quality',
    name: 'OrchestrationQualityDetails',
    component: orchestrationComponent,
    meta: {
      requiresAuth: true,
      hideFooter: true,
      orchestrationView: 'quality',
      orchestrationTaskDetail: 'quality',
    },
  },
  {
    path: '/orchestration/:view',
    name: 'OrchestrationView',
    component: orchestrationComponent,
    meta: { requiresAuth: true, hideFooter: true },
    beforeEnter: (to) => {
      const view = Array.isArray(to.params.view)
        ? to.params.view[0]
        : to.params.view
      if (!validOrchestrationViews.has(`${view}`)) {
        return '/orchestration/ingestion'
      }
    },
  },
  {
    path: '/hydroloader/download',
    name: 'HydroLoader',
    component: () => import('@/pages/HydroLoaderDownload.vue'),
  },
  {
    // AllAuth emails will link users to this page if a password reset was requested but the email provided does not
    // have an account associated with it yet.
    path: '/sign-up',
    name: 'SignUp',
    component: () => {
      if (disableAccountCreation === 'true') {
        return import('@/pages/PageNotFound.vue')
      } else {
        return import('@/pages/account/Signup.vue')
      }
    },
    meta: {
      requiresLoggedOut: true,
      title: 'Sign Up',
      metaTags: [
        {
          name: 'keywords',
          content: 'Sign Up, Account, User',
        },
      ],
    },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/account/Login.vue'),
    meta: {
      title: 'Login',
      requiresLoggedOut: true,
    },
  },
  {
    // AllAuth password reset emails will link users to this page. This page will need to request the user for a new
    // password and then POST the password and reset key to the resetPassword endpoint complete the password reset
    // process. Full docs here:
    // https://docs.allauth.org/en/dev/headless/openapi-specification/#tag/Authentication:-Password-Reset/paths/~1_allauth~1%7Bclient%7D~1v1~1auth~1password~1reset/post
    path: '/reset-password/:passwordResetKey?',
    name: 'ResetPassword',
    component: () => import('@/pages/account/ResetPassword.vue'),
    meta: {
      title: 'Reset Password',
    },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/pages/account/Profile.vue'),
    meta: { requiresAuth: true, title: 'Profile' },
  },
  {
    path: '/complete-profile',
    name: 'CompleteProfile',
    component: () => import('@/pages/account/CompleteProfile.vue'),
    meta: { title: 'Complete Profile' },
  },
  {
    // AllAuth verification emails will link users to this page. This page will need to POST a key to the verifyEmail
    // endpoint to complete the verification process. Full docs here:
    // https://docs.allauth.org/en/dev/headless/openapi-specification/#tag/Authentication:-Account/paths/~1_allauth~1%7Bclient%7D~1v1~1auth~1email~1verify/post
    path: '/verify-email',
    name: 'VerifyEmail',
    component: () => import('@/pages/account/VerifyEmail.vue'),
    meta: { title: 'Verify Email' },
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
