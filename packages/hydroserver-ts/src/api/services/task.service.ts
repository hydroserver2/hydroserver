import { HydroServerBaseService } from './base'
import { EtlTaskContract as C, RunContract } from '../../generated/contracts'
import {
  Task as M,
  StatusType,
  TaskExpanded,
  TaskRun,
} from '../Models/task.model'
import { apiMethods } from '../apiMethods'

export class TaskService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  runTask(taskId: string) {
    const url = `${this._route}/${taskId}`
    return apiMethods.post(url)
  }

  /* ----------------------- Sub-resources: Task Runs ----------------------- */

  getTaskRuns(taskId: string, params?: RunContract.QueryParameters) {
    const url = this.withQuery(`${this._route}/${taskId}/runs`, params)
    return apiMethods.paginatedFetch(url)
  }

  createTaskRun(taskId: string, body: RunContract.PostBody) {
    const url = `${this._route}/${taskId}/runs`
    return apiMethods.post(url, body)
  }

  getTaskRun(taskId: string, runId: string) {
    const url = `${this._route}/${taskId}/runs/${runId}`
    return apiMethods.fetch(url)
  }

  // Task runs are generated and never touched by users & devs
  // updateTaskRun(
  //   taskId: string,
  //   runId: string,
  //   body: RunContract.PatchBody,
  //   originalBody?: RunContract.PatchBody
  // ) {
  //   const url = `${this._route}/${taskId}/runs/${runId}`
  //   return apiMethods.patch(url, body, originalBody ?? null)
  // }

  // deleteTaskRun(taskId: string, runId: string) {
  //   const url = `${this._route}/${taskId}/runs/${runId}`
  //   return apiMethods.delete(url)
  // }

  /* ----------------------- Convenience Functions  ----------------------- */

  addMapping(task: M) {
    task.mappings.push({
      sourceIdentifier: '',
      paths: [{ targetIdentifier: '', dataTransformations: [] }],
    })
  }

  /**  Remove mapping path if datastream id is targetId. Remove mappings that now have no paths. */
  removeTarget(task: M, id: string | number): void {
    const key = String(id)
    for (const m of task.mappings) {
      m.paths = m.paths.filter((p) => String(p.targetIdentifier) !== key)
    }
    task.mappings = task.mappings.filter((m) => m.paths.length > 0)
  }

  getStatusText(task: TaskExpanded): StatusType {
    const { latestRun, schedule } = task
    // Don't crash the UI if a task isn't scheduled.
    if (!schedule) {
      if (!latestRun) return 'Pending'
      return latestRun.status === 'FAILURE' ? 'Needs attention' : 'OK'
    }

    if (schedule.paused) return 'Loading paused'
    if (!latestRun) return 'Pending'
    if (latestRun.status === 'FAILURE') return 'Needs attention'

    const { nextRunAt } = schedule
    const next = nextRunAt ? new Date(nextRunAt) : undefined
    if (next && !Number.isNaN(next.valueOf())) {
      return next.getTime() < Date.now() ? 'Behind schedule' : 'OK'
    }

    return 'Unknown'
  }

  getBadCountText(statusArray: TaskRun[]) {
    const badCount = statusArray.filter((s) => s.status === 'FAILED').length
    if (!badCount) return ''
    if (badCount === 1) return '1 error'
    return `${badCount} errors`
  }

  getBehindScheduleCountText(statusArray: TaskRun[]) {
    const behindCount = statusArray.filter(
      (s) => s.status === 'Behind schedule'
    ).length
    if (!behindCount) return ''
    return `${behindCount} behind schedule`
  }
}
