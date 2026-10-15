import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import EditableCell from '@/components/VisualizeData/EditableCell.vue'

const props = {
  value: '10',
  display: '10',
  edited: false,
  originalDisplay: '10',
  editedDisplay: '',
  inputType: 'number' as const,
}

const mountCell = (extra: Record<string, unknown> = {}) =>
  mount(EditableCell, {
    props: { ...props, ...extra },
    global: { plugins: [createTestVuetify()] },
  })

describe('EditableCell readonly', () => {
  it('opens an input on click when editable', async () => {
    const w = mountCell()
    await w.find('button.editable-cell__display').trigger('click')
    expect(w.find('input').exists()).toBe(true)
  })

  it('shows the value with no way to edit when readonly', () => {
    const w = mountCell({ readonly: true })
    expect(w.text()).toContain('10')
    expect(w.find('button').exists()).toBe(false)
  })

  it('closes an open input when it becomes readonly', async () => {
    const w = mountCell()
    await w.find('button.editable-cell__display').trigger('click')
    await w.setProps({ readonly: true })
    expect(w.find('input').exists()).toBe(false)
  })
})
