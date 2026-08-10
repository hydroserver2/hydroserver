import { RouteRecordRaw } from 'vue-router'
import { enableHomePage } from '@/config/homeConfig'
import hs from '@hydroserver/client'

const validOrchestrationViews = new Set(['ingestion', 'aggregation', 'quality'])

const orchestrationComponent = () => import('@/pages/Orchestration.vue')
const ingestionTaskDetailsComponent = () =>
  import('@/components/Orchestration/ingestion/IngestionTaskDetails.vue')
const aggregationTaskDetailsComponent = () =>
  import('@/components/Orchestration/data-products/AggregationTaskDetails.vue')
const expressionTaskDetailsComponent = () =>
  import('@/components/Orchestration/data-products/ExpressionTaskDetails.vue')
const derivationTaskDetailsComponent = () =>
  import('@/components/Orchestration/data-products/DerivationTaskDetails.vue')
const ratingCurveTaskDetailsComponent = () =>
  import('@/components/Orchestration/data-products/RatingCurveTaskDetails.vue')
const qualityTaskDetailsComponent = () =>
  import('@/components/Orchestration/monitoring/QualityTaskDetails.vue')

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
    path: '/workspaces',
    name: 'Workspaces',
    component: () => import('@/pages/Workspaces.vue'),
    meta: {
      requiresAuth: true,
      hideFooter: true,
      title: 'Manage Workspaces',
      metaTags: [
        {
          name: 'keywords',
          content: 'HydroServer, Workspaces, Access Control, Metadata',
        },
      ],
    },
  },
  {
    path: '/browse',
    name: 'Browse',
    component: () => import('@/pages/Browse.vue'),
    meta: {
      hideFooter: true,
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
    redirect: (to) => ({
      name: 'Browse',
      query: to.query,
      hash: to.hash,
    }),
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
    children: [
      {
        path: 'details/ingestion',
        name: 'OrchestrationIngestionDetails',
        component: ingestionTaskDetailsComponent,
        meta: {
          orchestrationView: 'ingestion',
          orchestrationTaskDetail: 'ingestion',
        },
      },
      {
        path: 'details/aggregation',
        name: 'OrchestrationAggregationDetails',
        component: aggregationTaskDetailsComponent,
        meta: {
          orchestrationView: 'aggregation',
          orchestrationTaskDetail: 'aggregation',
        },
      },
      {
        path: 'details/expression',
        name: 'OrchestrationExpressionDetails',
        component: expressionTaskDetailsComponent,
        meta: {
          orchestrationView: 'aggregation',
          orchestrationTaskDetail: 'expression',
        },
      },
      {
        path: 'details/derivation',
        name: 'OrchestrationDerivationDetails',
        component: derivationTaskDetailsComponent,
        meta: {
          orchestrationView: 'aggregation',
          orchestrationTaskDetail: 'derivation',
        },
      },
      {
        path: 'details/rating-curve',
        name: 'OrchestrationRatingCurveDetails',
        component: ratingCurveTaskDetailsComponent,
        meta: {
          orchestrationView: 'aggregation',
          orchestrationTaskDetail: 'rating-curve',
        },
      },
      {
        path: 'details/quality',
        name: 'OrchestrationQualityDetails',
        component: qualityTaskDetailsComponent,
        meta: {
          orchestrationView: 'quality',
          orchestrationTaskDetail: 'quality',
        },
      },
    ],
  },
  {
    path: '/streaming-data-loader/download',
    name: 'StreamingDataLoaderDownload',
    component: () => import('@/pages/StreamingDataLoaderDownload.vue'),
    meta: {
      title: 'Download Streaming Data Loader',
      metaTags: [
        {
          name: 'keywords',
          content: 'HydroServer, Streaming Data Loader, SDL, Download',
        },
      ],
    },
  },
  {
    // Renamed from /hydroloader/download. Kept as a redirect since this
    // page has already shipped to production and may be bookmarked or
    // linked from elsewhere.
    path: '/hydroloader/download',
    redirect: '/streaming-data-loader/download',
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
    // The Manage Metadata page now lives in the Workspaces page as a tab.
    path: '/metadata',
    name: 'Metadata',
    redirect: { path: '/workspaces', query: { section: 'metadata' } },
  },
  {
    path: '/access-denied',
    name: 'AccessDenied',
    component: () => import('@/pages/AccessDenied.vue'),
    meta: { requiresAuth: true, title: 'Access Denied' },
  },
  {
    path: '/visualize-data/:monitoringSiteId?',
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
