import type { ItemScope } from '@/composables/tableScope'

export interface MetadataItem {
  id: string
  _scope?: ItemScope
  name?: string
  code?: string | null
  type?: string
  symbol?: string
  description?: string
  definition?: string | null
  sensorModel?: string
  sensorModelManufacturer?: string
  sensorModelDefinition?: string
}
