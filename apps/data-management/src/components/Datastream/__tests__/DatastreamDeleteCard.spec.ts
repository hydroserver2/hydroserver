import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import vuetify from '@hydroserver/design-system/vue/vuetify'
import DatastreamDeleteCard from '../DatastreamDeleteCard.vue'

const mountCard = () =>
  mount(DatastreamDeleteCard, {
    props: {
      datastream: {
        id: 'datastream-1',
        name: 'Air Temperature - Daily Max, RAW',
      },
    },
    global: { plugins: [vuetify] },
  })

describe('datastream deletion confirmation', () => {
  it.each(['Delete', 'delete', 'dElEtE', '  Delete\u00a0'])(
    'accepts the confirmation word %j for a name containing punctuation',
    async (input) => {
      const wrapper = mountCard()
      await wrapper.get('input').setValue(input)
      await wrapper.get('input').trigger('keydown', { key: 'Enter' })
      expect(wrapper.emitted('delete')).toHaveLength(1)
      expect(wrapper.emitted('close')).toHaveLength(1)
      wrapper.unmount()
    }
  )

  it.each(['', 'Air Temperature - Daily Max, RAW', 'delete this'])(
    'keeps the dialog open and explains how to correct %j',
    async (input) => {
      const wrapper = mountCard()
      await wrapper.get('input').setValue(input)
      const confirm = wrapper
        .findAll('button')
        .find((button) => button.text() === 'Confirm')!
      await confirm.trigger('click')
      expect(wrapper.emitted('delete')).toBeUndefined()
      expect(wrapper.emitted('close')).toBeUndefined()
      expect(wrapper.text()).toContain('Type Delete to confirm deletion.')

      await wrapper.get('input').setValue('Delete')
      await confirm.trigger('click')
      expect(wrapper.emitted('delete')).toHaveLength(1)
      expect(wrapper.emitted('close')).toHaveLength(1)
      wrapper.unmount()
    }
  )

  it('cancels without deleting', async () => {
    const wrapper = mountCard()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Cancel')!
      .trigger('click')
    expect(wrapper.emitted('delete')).toBeUndefined()
    expect(wrapper.emitted('close')).toHaveLength(1)
    wrapper.unmount()
  })
})
