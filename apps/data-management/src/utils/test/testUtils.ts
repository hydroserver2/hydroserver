import {
  createMemoryHistory,
  createRouter,
  type RouteLocationRaw,
  type Router,
} from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ResizeObserverPolyfill from 'resize-observer-polyfill'
import { routes } from '@/router/routes'

const vuetify = createVuetify({
  components,
  directives,
})

global.ResizeObserver = ResizeObserverPolyfill

export function createTestRouter(base?: string): Router {
  return createRouter({
    routes,
    history: createMemoryHistory(base),
  })
}

interface RenderOptionsArgs {
  props: Record<string, unknown>
  slots: Record<string, (...args: unknown[]) => unknown>

  router?: Router
  initialRoute: RouteLocationRaw

  initialState: Record<string, unknown>
  stubActions: boolean
}

export function renderOptions(args: Partial<RenderOptionsArgs> = {}) {
  const localRouter = args.router || createTestRouter()

  const result = {
    props: args.props,
    slots: args.slots,
    global: {
      plugins: [vuetify, localRouter],
    },
  }

  return result
}

export function wrapTestComponent(component: any) {
  return {
    components: { 'test-component': component },
    template: `
        <v-app>
          <v-main>
            <test-component />
          </v-main>
        </v-app>
        `,
  }
}
