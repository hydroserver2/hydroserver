/**
 * Unit tests for PlotSourceDialog.vue — the chooser shown when plotting a
 * source datastream that has managed (QC) datastreams derived from it.
 * Purely presentational, so no stores are mocked.
 */

import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import PlotSourceDialog from '../PlotSourceDialog.vue'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const source = {
  id: 'src',
  name: 'Logan River Temp',
  valueCount: 1000,
  processingLevel: { definition: 'Raw' },
} as any

const options = [
  {
    historyId: 'h-1',
    managed: {
      id: 'mgd-1',
      name: 'Logan River Temp (QC)',
      valueCount: 900,
      processingLevel: { definition: 'Quality controlled' },
    },
    sessions: [{ id: 's-1', status: 'in_progress' }],
  },
  {
    historyId: 'h-2',
    managed: { id: 'mgd-2', name: 'Logan River Temp (QC2)', valueCount: 800 },
    sessions: [],
  },
] as any

const mountDialog = (props: Record<string, any> = {}) =>
  mount(PlotSourceDialog, {
    props: {
      source,
      options,
      plottedIds: [],
      slotsLeft: 5,
      ...props,
    },
    global: { plugins: [createTestVuetify()] },
  })

const optionInput = (wrapper: any, id: string) =>
  wrapper.find(`[data-testid="plot-option-${id}"] input`)

describe('PlotSourceDialog', () => {
  it('lists the raw datastream first, then one row per managed datastream', () => {
    const wrapper = mountDialog()
    const labels = wrapper
      .findAll('[data-testid^="plot-option-"]')
      .map((el) => el.attributes('data-testid'))
    expect(labels).toEqual([
      'plot-option-src',
      'plot-option-mgd-1',
      'plot-option-mgd-2',
    ])
    expect(wrapper.text()).toContain('Raw data')
    expect(wrapper.text()).toContain('Logan River Temp (QC)')
  })

  it('shows a summary line for each managed datastream', () => {
    const wrapper = mountDialog()
    expect(wrapper.text()).toContain('Level: Quality controlled')
    expect(wrapper.text()).toContain('1 session, 1 in progress')
    expect(wrapper.text()).toContain('0 sessions')
  })

  it('starts with the already-plotted series checked', () => {
    const wrapper = mountDialog({ plottedIds: ['mgd-1'] })
    expect(
      (optionInput(wrapper, 'mgd-1').element as HTMLInputElement).checked
    ).toBe(true)
    expect(
      (optionInput(wrapper, 'src').element as HTMLInputElement).checked
    ).toBe(false)
  })

  it('shows a spinner and no rows while loading', () => {
    const wrapper = mountDialog({ loading: true, options: [] })
    expect(wrapper.findAll('[data-testid^="plot-option-"]')).toHaveLength(0)
    expect(wrapper.find('.v-progress-circular').exists()).toBe(true)
  })

  it('emits the checked ids in display order, not click order', async () => {
    const wrapper = mountDialog()
    await optionInput(wrapper, 'mgd-2').setValue(true)
    await optionInput(wrapper, 'src').setValue(true)
    await wrapper.find('[data-testid="plot-source-apply"]').trigger('click')
    expect(wrapper.emitted('apply')?.[0]).toEqual([['src', 'mgd-2']])
  })

  it('emits an empty selection when everything is unchecked', async () => {
    const wrapper = mountDialog({ plottedIds: ['src'] })
    await optionInput(wrapper, 'src').setValue(false)
    await wrapper.find('[data-testid="plot-source-apply"]').trigger('click')
    expect(wrapper.emitted('apply')?.[0]).toEqual([[]])
  })

  it('disables unchecked rows once the plot cap is reached', async () => {
    const wrapper = mountDialog({ plottedIds: ['src'], slotsLeft: 1 })
    expect(optionInput(wrapper, 'mgd-1').attributes('disabled')).toBeDefined()
    // The checked one stays enabled so the selection can still be changed.
    expect(optionInput(wrapper, 'src').attributes('disabled')).toBeUndefined()
    expect(wrapper.find('[data-testid="plot-source-cap"]').exists()).toBe(true)

    await optionInput(wrapper, 'src').setValue(false)
    expect(optionInput(wrapper, 'mgd-1').attributes('disabled')).toBeUndefined()
  })

  it('emits cancel without a selection', async () => {
    const wrapper = mountDialog()
    await wrapper.find('[data-testid="plot-source-cancel"]').trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(wrapper.emitted('apply')).toBeUndefined()
  })
})
