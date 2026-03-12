import { HydroServerBaseService } from './base'
import { EtlOrchestrationSystemContract as C } from '../../generated/contracts'

export interface OrchestrationSystem {
  name: string
  id: string
  workspaceId: string
  type: string
}

export class OrchestrationSystemService extends HydroServerBaseService<
  typeof C,
  OrchestrationSystem
> {
  static route = C.route
  static writableKeys = C.writableKeys
}
