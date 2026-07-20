import { HydroServerBaseService } from './base'
import { TaskContract as C, RunContract } from '../../generated/contracts'
import { Task as M, type TaskRun } from '../Models/task.model'
import { apiMethods } from '../apiMethods'

export class TaskService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  protected override getBaseUrl(): string {
    return this._client.etlDataBase
  }

  runTask(taskId: string) {
    return apiMethods.post<TaskRun>(`${this._route}/${taskId}/trigger`)
  }

  getTaskRuns(taskId: string, params?: RunContract.QueryParameters) {
    return apiMethods.paginatedFetch<TaskRun[]>(
      this.withQuery(`${this._route}/${taskId}/runs`, params)
    )
  }

  getTaskRun(taskId: string, runId: string) {
    return apiMethods.fetch<TaskRun>(`${this._route}/${taskId}/runs/${runId}`)
  }
}
