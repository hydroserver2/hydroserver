import { HydroServerBaseService } from './base'
import { DataProductTransformationContract as C } from '../../generated/contracts'
import type { DataProductTransformation as M } from './data-product-transformation.types'

export class DataProductTransformationService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
}
