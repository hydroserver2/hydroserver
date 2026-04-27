import { HydroServerBaseService } from './base'
import { TaskContract as C, RunContract } from '../../generated/contracts'
import { Task as M } from '../Models/task.model'
import { apiMethods } from '../apiMethods'

export class TaskService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  protected override getBaseUrl(): string {
    return this._client.etlDataBase
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

  addMapping(task: M) {
    task.mappings.push({
      sourceIdentifier: '',
      paths: [{ targetIdentifier: '', dataTransformations: [] }],
    } as any)
  }

  removeTarget(task: M, targetIdentifier: string | number) {
    for (const mapping of task.mappings as any[]) {
      mapping.paths = (mapping.paths ?? []).filter(
        (path: any) => String(path.targetIdentifier) !== String(targetIdentifier)
      )
    }
    task.mappings = (task.mappings as any[]).filter(
      (mapping) => (mapping.paths ?? []).length > 0
    ) as any
  }
}
