import { UserService, SessionService, WorkspaceService } from './services'
import { MonitoringSiteService } from './services/monitoring-site.service'
import { MonitoringSiteTypeService } from './services/monitoring-site-type.service'
import { LinkedResourceTypeService } from './services/linked-resource-type.service'
import { ObservedPropertyService } from './services/observed-property.service'
import { ObservedPropertyTypeService } from './services/observed-property-type.service'
import { UnitService } from './services/unit.service'
import { UnitTypeService } from './services/unit-type.service'
import { ProcessingLevelService } from './services/processing-level.service'
import { ResultQualifierService } from './services/result-qualifier.service'
import { SampledMediumService } from './services/sampled-medium.service'
import { AggregationStatisticService } from './services/aggregation-statistic.service'
import { DatastreamStatusService } from './services/datastream-status.service'
import { DatastreamService } from './services/datastream.service'
import { MethodService } from './services/method.service'
import { MethodTypeService } from './services/method-type.service'
import { DataConnectionService } from './services/data-connection.service'
import { TaskService } from './services/task.service'
import { EtlMappingService } from './services/etl-mapping.service'
import { MonitoringTaskService } from './services/monitoring-task.service'
import { MonitoringRuleService } from './services/monitoring-rule.service'
import { DataProductTaskService } from './services/data-product-task.service'
import { DataProductTransformationService } from './services/data-product-transformation.service'
import { RatingCurveService } from './services/rating-curve.service'
import { RatingCurvePreviewService } from './services/rating-curve-preview.service'
import {
  QualityControlHistoryService,
  QualityControlOperationService,
  QualityControlSessionService,
} from './services/quality-control.service'

export type AuthTuple = [string, string]

export interface HydroServerOIDCOptions {
  clientId: string
  redirectPath?: string
  postLogoutRedirectPath?: string
  scope?: string
}

export interface HydroServerOptions {
  host: string
  oidc?: HydroServerOIDCOptions
}

export class HydroServer {
  readonly host: string
  readonly resolvedHost: string
  readonly baseRoute: string
  readonly oidc?: Required<HydroServerOIDCOptions>

  private _workspaces?: WorkspaceService
  private _monitoringSites?: MonitoringSiteService
  private _monitoringSiteTypes?: MonitoringSiteTypeService
  private _linkedResourceTypes?: LinkedResourceTypeService
  private _observedProperties?: ObservedPropertyService
  private _observedPropertyTypes?: ObservedPropertyTypeService
  private _units?: UnitService
  private _unitTypes?: UnitTypeService
  private _processingLevels?: ProcessingLevelService
  private _resultQualifiers?: ResultQualifierService
  private _sampledMediums?: SampledMediumService
  private _aggregationStatistics?: AggregationStatisticService
  private _datastreamStatuses?: DatastreamStatusService
  private _methods?: MethodService
  private _methodTypes?: MethodTypeService
  private _datastreams?: DatastreamService
  private _session?: SessionService
  private _user?: UserService

  private _dataConnections?: DataConnectionService
  private _tasks?: TaskService
  private _etlMappings?: EtlMappingService
  private _monitoringTasks?: MonitoringTaskService
  private _monitoringRules?: MonitoringRuleService
  private _dataProductTasks?: DataProductTaskService
  private _dataProductTransformations?: DataProductTransformationService
  private _ratingCurves?: RatingCurveService
  private _ratingCurvePreview?: RatingCurvePreviewService
  private _qualityControlHistories?: QualityControlHistoryService
  private _qualityControlSessions?: QualityControlSessionService
  private _qualityControlOperations?: QualityControlOperationService

  constructor(opts: HydroServerOptions) {
    const { host, oidc } = opts
    this.host = host.trim().replace(/\/+$/, '')
    this.resolvedHost = this.host || globalThis.location?.origin || ''
    this.baseRoute = `${this.host}/api/data`
    this.oidc = oidc
      ? {
          clientId: oidc.clientId,
          redirectPath: oidc.redirectPath ?? '/callback',
          postLogoutRedirectPath: oidc.postLogoutRedirectPath ?? '/',
          scope: oidc.scope ?? 'openid profile email',
        }
      : undefined
  }

  static async initialize(options: HydroServerOptions): Promise<HydroServer> {
    const client = new HydroServer(options)
    await client.session.initialize()
    return client
  }

  private listeners: Record<string, Array<(...args: unknown[]) => void>> = {}

  public on(eventName: string, callback: (...args: unknown[]) => void): void {
    ;(this.listeners[eventName] ??= []).push(callback)
  }

  public emit(eventName: string, ...args: unknown[]): void {
    for (const callback of this.listeners[eventName] ?? []) {
      callback(...args)
    }
  }

  resolveUrl(path: string): string {
    if (!this.resolvedHost) return path
    return new URL(path, this.resolvedHost).toString()
  }

  resolveAppUrl(path: string): string {
    const base = globalThis.location?.origin || this.resolvedHost
    if (!base) return path
    return new URL(path, base).toString()
  }

  get workspaces(): WorkspaceService {
    return (this._workspaces ??= new WorkspaceService(this))
  }
  get monitoringSites(): MonitoringSiteService {
    return (this._monitoringSites ??= new MonitoringSiteService(this))
  }
  get monitoringSiteTypes(): MonitoringSiteTypeService {
    return (this._monitoringSiteTypes ??= new MonitoringSiteTypeService(this))
  }
  get linkedResourceTypes(): LinkedResourceTypeService {
    return (this._linkedResourceTypes ??= new LinkedResourceTypeService(this))
  }
  get observedProperties(): ObservedPropertyService {
    return (this._observedProperties ??= new ObservedPropertyService(this))
  }
  get observedPropertyTypes(): ObservedPropertyTypeService {
    return (this._observedPropertyTypes ??= new ObservedPropertyTypeService(this))
  }
  get units(): UnitService {
    return (this._units ??= new UnitService(this))
  }
  get unitTypes(): UnitTypeService {
    return (this._unitTypes ??= new UnitTypeService(this))
  }
  get processingLevels(): ProcessingLevelService {
    return (this._processingLevels ??= new ProcessingLevelService(this))
  }
  get resultQualifiers(): ResultQualifierService {
    return (this._resultQualifiers ??= new ResultQualifierService(this))
  }
  get sampledMediums(): SampledMediumService {
    return (this._sampledMediums ??= new SampledMediumService(this))
  }
  get aggregationStatistics(): AggregationStatisticService {
    return (this._aggregationStatistics ??= new AggregationStatisticService(this))
  }
  get datastreamStatuses(): DatastreamStatusService {
    return (this._datastreamStatuses ??= new DatastreamStatusService(this))
  }
  get methods(): MethodService {
    return (this._methods ??= new MethodService(this))
  }
  get methodTypes(): MethodTypeService {
    return (this._methodTypes ??= new MethodTypeService(this))
  }
  get datastreams(): DatastreamService {
    return (this._datastreams ??= new DatastreamService(this))
  }
  get dataConnections(): DataConnectionService {
    return (this._dataConnections ??= new DataConnectionService(this))
  }
  get tasks(): TaskService {
    return (this._tasks ??= new TaskService(this))
  }
  get etlMappings(): EtlMappingService {
    return (this._etlMappings ??= new EtlMappingService(this))
  }
  get monitoringTasks(): MonitoringTaskService {
    return (this._monitoringTasks ??= new MonitoringTaskService(this))
  }
  get monitoringRules(): MonitoringRuleService {
    return (this._monitoringRules ??= new MonitoringRuleService(this))
  }
  get dataProductTasks(): DataProductTaskService {
    return (this._dataProductTasks ??= new DataProductTaskService(this))
  }
  get dataProductTransformations(): DataProductTransformationService {
    return (this._dataProductTransformations ??=
      new DataProductTransformationService(this))
  }
  get ratingCurves(): RatingCurveService {
    return (this._ratingCurves ??= new RatingCurveService(this))
  }
  get ratingCurvePreview(): RatingCurvePreviewService {
    return (this._ratingCurvePreview ??= new RatingCurvePreviewService(this))
  }
  get qualityControlHistories(): QualityControlHistoryService {
    return (this._qualityControlHistories ??= new QualityControlHistoryService(
      this
    ))
  }
  get qualityControlSessions(): QualityControlSessionService {
    return (this._qualityControlSessions ??= new QualityControlSessionService(
      this
    ))
  }
  get qualityControlOperations(): QualityControlOperationService {
    return (this._qualityControlOperations ??=
      new QualityControlOperationService(this))
  }
  get session(): SessionService {
    return (this._session ??= new SessionService(this))
  }
  get user(): UserService {
    return (this._user ??= new UserService(this))
  }
}
