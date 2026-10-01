import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// vi.mock factories are hoisted above module-level consts, so anything they
// close over has to be created inside vi.hoisted.
const { datastreams, resumeDatastreamId, error } = vi.hoisted(() => {
  const { ref: r } = require('vue') as typeof import('vue')
  return {
    datastreams: r<any[]>([]),
    resumeDatastreamId: r<string | null>(null),
    error: vi.fn(),
  }
})

// Real Pinia stores, so `storeToRefs` behaves as it does in production.
vi.mock('@/store/dataVisualization', async () => {
  const { defineStore } = await import('pinia')
  return {
    useDataVisStore: defineStore('dataVisualization', () => ({ datastreams })),
  }
})

vi.mock('@/store/qcSession', async () => {
  const { defineStore } = await import('pinia')
  return {
    useQcSessionStore: defineStore('qcSession', () => ({
      resumeDatastreamId,
    })),
  }
})

vi.mock('@uwrl/qc-utils', () => ({ Snackbar: { error } }))

import { useResumeEditSession } from '../useResumeEditSession'

const resume = vi.fn()

let pinia: ReturnType<typeof createPinia>
// The stores are module-level refs shared across tests, so a host left
// mounted keeps watching them and resumes again in the next test.
let hosts: ReturnType<typeof mount>[] = []

const mountHost = () => {
  const wrapper = mount(
    defineComponent({
      setup() {
        useResumeEditSession(resume)
        return () => null
      },
    }),
    { global: { plugins: [pinia] } }
  )
  hosts.push(wrapper)
  return wrapper
}

afterEach(() => {
  hosts.forEach((h) => h.unmount())
  hosts = []
})

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
  vi.clearAllMocks()
  resume.mockResolvedValue(undefined)
  datastreams.value = []
  resumeDatastreamId.value = null
})

describe('useResumeEditSession', () => {
  // The catalog is empty at mount on a cold reload, which is the whole
  // point of this composable. An `immediate` + `once` watcher burns its
  // single firing on that empty list and never sees the catalog land.
  it('resumes when the catalog arrives after mount', async () => {
    resumeDatastreamId.value = 'mgd-1'
    mountHost()
    expect(resume).not.toHaveBeenCalled()

    datastreams.value = [{ id: 'mgd-1' }]
    await flushPromises()

    expect(resume).toHaveBeenCalledWith('mgd-1')
  })

  it('resumes immediately when the catalog is already loaded', async () => {
    resumeDatastreamId.value = 'mgd-1'
    datastreams.value = [{ id: 'mgd-1' }]
    mountHost()
    await flushPromises()
    expect(resume).toHaveBeenCalledWith('mgd-1')
  })

  it('does nothing without a stored session', async () => {
    datastreams.value = [{ id: 'mgd-1' }]
    mountHost()
    await flushPromises()
    expect(resume).not.toHaveBeenCalled()
  })

  it('drops a pointer to a datastream missing from the catalog', async () => {
    resumeDatastreamId.value = 'gone'
    mountHost()
    datastreams.value = [{ id: 'mgd-1' }]
    await flushPromises()

    expect(resume).not.toHaveBeenCalled()
    expect(resumeDatastreamId.value).toBeNull()
  })

  it('only resumes once, so a later catalog refresh does not re-enter', async () => {
    resumeDatastreamId.value = 'mgd-1'
    mountHost()
    datastreams.value = [{ id: 'mgd-1' }]
    await flushPromises()
    expect(resume).toHaveBeenCalledTimes(1)

    datastreams.value = [{ id: 'mgd-1' }, { id: 'mgd-2' }]
    await flushPromises()
    expect(resume).toHaveBeenCalledTimes(1)
  })

  // Entering the editor sets the pointer itself, and a later catalog
  // refresh (a commit rewrites the managed datastream) must not re-enter
  // behind the user's back.
  it('ignores a pointer set after the catalog landed', async () => {
    datastreams.value = [{ id: 'mgd-1' }]
    mountHost()
    await flushPromises()

    resumeDatastreamId.value = 'mgd-1'
    datastreams.value = [{ id: 'mgd-1' }, { id: 'mgd-2' }]
    await flushPromises()

    expect(resume).not.toHaveBeenCalled()
    expect(resumeDatastreamId.value).toBe('mgd-1')
  })

  it('surfaces a failure instead of failing silently', async () => {
    resumeDatastreamId.value = 'mgd-1'
    resume.mockRejectedValueOnce(new Error('boom'))
    mountHost()
    datastreams.value = [{ id: 'mgd-1' }]
    await flushPromises()

    expect(error).toHaveBeenCalledWith('boom')
    expect(resumeDatastreamId.value).toBeNull()
  })
})
