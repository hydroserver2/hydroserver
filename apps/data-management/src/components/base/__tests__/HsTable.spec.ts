import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { HsTable } from '@hydroserver/design-system/vue'

describe('HsTable', () => {
  it('shows the shared selection header and emits clear-selection', async () => {
    const wrapper = mount(HsTable, {
      props: {
        title: 'Datastreams',
        columnCount: 2,
        count: 12,
        selectionCount: 2,
        selectionLimit: 5,
      },
      slots: {
        filters: '<button>Filters</button>',
        'selection-actions': '<button>Download selected</button>',
        default: '<tr><td>Site</td><td>Temperature</td></tr>',
      },
    })

    expect(wrapper.text()).toContain('12 available')
    expect(wrapper.text()).toContain('2 of 5 selected')
    expect(wrapper.text()).toContain('Download selected')
    expect(wrapper.text()).not.toContain('Filters')

    await wrapper
      .get('input[aria-label="Clear selected rows"]')
      .trigger('change')
    expect(wrapper.emitted('clear-selection')).toHaveLength(1)
  })
})
