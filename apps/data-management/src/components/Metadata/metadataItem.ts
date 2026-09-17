import type { ItemScope } from '@/composables/tableScope'

export interface MetadataItem {
  id: string
  _scope?: ItemScope
  name?: string
  code?: string
  type?: string
  symbol?: string
  description?: string
  definition?: string
  sensorModel?: string
  sensorModelManufacturer?: string
  sensorModelDefinition?: string
}
