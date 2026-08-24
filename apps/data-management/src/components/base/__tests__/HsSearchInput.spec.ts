import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import HsSearchInput from '@/components/base/HsSearchInput.vue'

describe('HsSearchInput', () => {
  it('clears the search from the trailing button', async () => {
    const wrapper = mount(HsSearchInput, {
      props: {
        modelValue: 'temperature',
        placeholder: 'Search metadata…',
      },
      global: {
        stubs: {
          'v-icon': true,
        },
      },
    })

    await wrapper.get('button[aria-label="Clear search"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')).toEqual([['']])
  })
})
