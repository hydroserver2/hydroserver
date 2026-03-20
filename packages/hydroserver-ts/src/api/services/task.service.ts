import { HydroServerBaseService } from './base'
import { EtlTaskContract as C, RunContract } from '../../generated/contracts'
import { Task as M } from '../Models/task.model'
import { apiMethods } from '../apiMethods'

export class TaskService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  runTask(taskId: string) {
    return apiMethods.post(`${this._route}/${taskId}`)
  }

  getTaskRuns(taskId: string, params?: RunContract.QueryParameters) {
    return apiMethods.paginatedFetch(
      this.withQuery(`${this._route}/${taskId}/runs`, params)
    )
  }

  createTaskRun(taskId: string, body: RunContract.PostBody) {
    return apiMethods.post(`${this._route}/${taskId}/runs`, body)
  }

  getTaskRun(taskId: string, runId: string) {
    return apiMethods.fetch(`${this._route}/${taskId}/runs/${runId}`)
  }

  addMapping(task: M) {
    task.mappings.push({
      sourceIdentifier: '',
      paths: [{ targetIdentifier: '', dataTransformations: [] }],
    })
  }

  removeTarget(task: M, id: string | number): void {
    const key = String(id)
    for (const mapping of task.mappings) {
      mapping.paths = mapping.paths.filter(
        (path) => String(path.targetIdentifier) !== key
      )
    }
    task.mappings = task.mappings.filter((mapping) => mapping.paths.length > 0)
  }
}
