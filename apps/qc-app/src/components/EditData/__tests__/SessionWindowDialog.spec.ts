import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, afterEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { createTestVuetify } from '@/utils/test/vuetify'
import SessionWindowDialog from '@/components/EditData/SessionWindowDialog.vue'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as any).visualViewport ||= {
  addEventListener() {},
  removeEventListener() {},
  offsetLeft: 0,
  offsetTop: 0,
  width: 1024,
  height: 768,
  scale: 1,
}

const DatePickerStub = defineComponent({
  props: { modelValue: { type: Date, required: true } },
  emits: ['update:modelValue'],
  setup(props, { attrs }) {
    return () =>
      h('input', {
        ...attrs,
        value: props.modelValue.toISOString(),
      })
  },
})

const source = {
  phenomenonBeginTime: '2025-01-01T00:00:00Z',
  phenomenonEndTime: '2025-12-31T00:00:00Z',
}
const sessions = [
  {
    status: 'committed',
    phenomenonTimeStart: '2025-01-01T00:00:00Z',
    phenomenonTimeEnd: '2025-05-01T00:00:00Z',
  },
]

let wrapper: ReturnType<typeof mount> | null = null
afterEach(() => {
  wrapper?.unmount()
  wrapper = null
})

const mountDialog = (props: Record<string, unknown> = {}) => {
  wrapper = mount(SessionWindowDialog, {
    props: { managedName: 'Temp (QC)', source, sessions, ...props },
    global: {
      plugins: [createTestVuetify()],
      stubs: { DatePickerField: DatePickerStub },
    },
    attachTo: document.body,
  })
  return wrapper
}

const pickers = (w: ReturnType<typeof mount>) =>
  w.findAllComponents(DatePickerStub)

describe('SessionWindowDialog', () => {
  it('prefills the window with the whole source extent', () => {
    const w = mountDialog()
    const [from, to] = pickers(w)
    expect((from!.props('modelValue') as Date).toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect((to!.props('modelValue') as Date).toISOString()).toBe('2025-12-31T00:00:00.000Z')
    expect(w.find('[data-testid="session-window-error"]').exists()).toBe(false)
  })

  it('shows the committed history range', () => {
    const w = mountDialog()
    expect(w.find('[data-testid="session-window-committed"]').text()).not.toMatch(/Nothing committed/)
  })

  it('says when nothing is committed yet', () => {
    const w = mountDialog({ sessions: [] })
    expect(w.find('[data-testid="session-window-committed"]').text()).toMatch(/Nothing committed yet/)
  })

  it('emits the window on Start', async () => {
    const w = mountDialog()
    await w.find('[data-testid="session-window-start"]').trigger('click')
    const [window] = w.emitted('confirm')![0] as [{ begin: Date; end: Date }]
    expect(window.begin.toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect(window.end.toISOString()).toBe('2025-12-31T00:00:00.000Z')
  })

  it('blocks Start when the committed history sits outside the source', () => {
    const w = mountDialog({
      sessions: [
        {
          status: 'committed',
          phenomenonTimeStart: '2026-03-01T00:00:00Z',
          phenomenonTimeEnd: '2026-04-01T00:00:00Z',
        },
      ],
    })
    expect(w.find('[data-testid="session-window-error"]').text()).toMatch(/gap before/)
    expect(w.find('[data-testid="session-window-start"]').attributes('disabled')).toBeDefined()
  })

  it('blocks Start and explains a gap after the history', async () => {
    const w = mountDialog()
    pickers(w)[0]!.vm.$emit('update:modelValue', new Date('2025-07-01T00:00:00Z'))
    await flushPromises()
    expect(w.find('[data-testid="session-window-error"]').text()).toMatch(/gap after/)
    expect(w.find('[data-testid="session-window-start"]').attributes('disabled')).toBeDefined()
  })

  it('emits cancel', async () => {
    const w = mountDialog()
    await w.find('[data-testid="session-window-cancel"]').trigger('click')
    expect(w.emitted('cancel')).toHaveLength(1)
  })
})

describe('SessionWindowDialog presets', () => {
  const preset = (w: ReturnType<typeof mount>, id: string) =>
    w.find(`[data-testid="session-window-preset-${id}"]`)

  it('offers the record spans, plus one starting at the committed end', () => {
    const w = mountDialog()
    for (const id of ['all', '1y', '6m', '1m', 'since']) {
      expect(preset(w, id).exists()).toBe(true)
    }
  })

  it('leaves out the committed preset when nothing is committed', () => {
    const w = mountDialog({ sessions: [] })
    expect(preset(w, 'since').exists()).toBe(false)
    expect(preset(w, 'all').exists()).toBe(true)
  })

  it('sets both fields from a preset', async () => {
    const w = mountDialog()
    await preset(w, 'since').trigger('click')
    await flushPromises()
    const [from, to] = pickers(w)
    expect((from!.props('modelValue') as Date).toISOString()).toBe('2025-05-01T00:00:00.000Z')
    expect((to!.props('modelValue') as Date).toISOString()).toBe('2025-12-31T00:00:00.000Z')
    expect(w.find('[data-testid="session-window-error"]').exists()).toBe(false)
  })

  it('disables a preset that would break a rule and says why', () => {
    const w = mountDialog()
    expect(preset(w, '1m').attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="session-window-preset-slot-1m"]').attributes('title')).toBe(
      'Leaves a gap after the committed work'
    )
    expect(preset(w, 'all').attributes('disabled')).toBeUndefined()
  })

  it('marks the preset matching the current window', async () => {
    const w = mountDialog()
    expect(preset(w, 'all').attributes('aria-pressed')).toBe('true')
    await preset(w, 'since').trigger('click')
    await flushPromises()
    expect(preset(w, 'since').attributes('aria-pressed')).toBe('true')
    expect(preset(w, 'all').attributes('aria-pressed')).toBe('false')
  })
})

describe('SessionWindowDialog one-click fix', () => {
  const fix = (w: ReturnType<typeof mount>) =>
    w.find('[data-testid="session-window-fix"]')

  it('offers the nearest valid start and leaves the end alone', async () => {
    const w = mountDialog()
    pickers(w)[0]!.vm.$emit('update:modelValue', new Date('2025-07-01T00:00:00Z'))
    await flushPromises()
    expect(fix(w).exists()).toBe(true)

    await fix(w).trigger('click')
    await flushPromises()
    const [from, to] = pickers(w)
    expect((from!.props('modelValue') as Date).toISOString()).toBe('2025-05-01T00:00:00.000Z')
    expect((to!.props('modelValue') as Date).toISOString()).toBe('2025-12-31T00:00:00.000Z')
    expect(w.find('[data-testid="session-window-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="session-window-start"]').attributes('disabled')).toBeUndefined()
  })

  it('offers the nearest valid end and leaves the start alone', async () => {
    const w = mountDialog()
    pickers(w)[1]!.vm.$emit('update:modelValue', new Date('2026-06-01T00:00:00Z'))
    await flushPromises()
    expect(fix(w).text()).toMatch(/^End at/)

    await fix(w).trigger('click')
    await flushPromises()
    const [from, to] = pickers(w)
    expect((from!.props('modelValue') as Date).toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect((to!.props('modelValue') as Date).toISOString()).toBe('2025-12-31T00:00:00.000Z')
    expect(w.find('[data-testid="session-window-error"]').exists()).toBe(false)
  })

  it('offers no fix when no single correction would be valid', () => {
    const w = mountDialog({
      sessions: [
        {
          status: 'committed',
          phenomenonTimeStart: '2026-03-01T00:00:00Z',
          phenomenonTimeEnd: '2026-04-01T00:00:00Z',
        },
      ],
    })
    expect(w.find('[data-testid="session-window-error"]').exists()).toBe(true)
    expect(fix(w).exists()).toBe(false)
  })
})
