import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import vuetify from '@hydroserver/design-system/vue/vuetify'
import DeleteDataConnectionCard from '../DeleteDataConnectionCard.vue'

describe('data connection deletion confirmation', () => {
  it('requires confirmation before deleting and accepts Enter', async () => {
    const wrapper = mount(DeleteDataConnectionCard, {
      props: { itemName: 'River connection' },
      global: { plugins: [vuetify] },
    })
    const confirm = wrapper.findAll('button').find((button) => button.text() === 'Confirm')!
    await confirm.trigger('click')
    expect(wrapper.emitted('delete')).toBeUndefined()
    expect(wrapper.emitted('close')).toBeUndefined()
    expect(wrapper.text()).toContain('Type Delete to confirm deletion.')

    await wrapper.get('input').setValue('  DELETE  ')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('delete')).toHaveLength(1)
    expect(wrapper.emitted('close')).toHaveLength(1)
    wrapper.unmount()
  })

  it('cancels without deleting', async () => {
    const wrapper = mount(DeleteDataConnectionCard, {
      props: { itemName: 'River connection' },
      global: { plugins: [vuetify] },
    })
    await wrapper.findAll('button').find((button) => button.text() === 'Cancel')!.trigger('click')
    expect(wrapper.emitted('delete')).toBeUndefined()
    expect(wrapper.emitted('close')).toHaveLength(1)
    wrapper.unmount()
  })
})
