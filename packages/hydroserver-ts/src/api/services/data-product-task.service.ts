import { HydroServerBaseService } from './base'
import { DataProductTaskContract as C, RunContract } from '../../generated/contracts'
import { DataProductTask as M } from '../Models/data-product-task.model'
import { apiMethods } from '../apiMethods'

export class DataProductTaskService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  protected override getBaseUrl(): string {
    return `${this._client.host}/api/data/products`
  }

  runTask(taskId: string) {
    return apiMethods.post(`${this._route}/${taskId}/trigger`)
  }

  getTaskRuns(taskId: string, params?: RunContract.QueryParameters) {
    return apiMethods.paginatedFetch(
      this.withQuery(`${this._route}/${taskId}/runs`, params)
    )
  }

  getTaskRun(taskId: string, runId: string) {
    return apiMethods.fetch(`${this._route}/${taskId}/runs/${runId}`)
  }
}
