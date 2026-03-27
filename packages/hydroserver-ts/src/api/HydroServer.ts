import { UserService, SessionService, WorkspaceService } from './services'
import { ThingService } from './services/thing.service'
import { ObservedPropertyService } from './services/observed-property.service'
import { UnitService } from './services/unit.service'
import { ProcessingLevelService } from './services/processing-level.service'
import { ResultQualifierService } from './services/result-qualifier.service'
import { DatastreamService } from './services/datastream.service'
import { SensorService } from './services/sensor.service'
import { OrchestrationSystemService } from './services/orchestration-system.service'
import { DataConnectionService } from './services/data-connection.service'
import { TaskService } from './services/task.service'
import { ThingFileAttachmentService } from './services/thing-file-attachment.service'

export type AuthTuple = [string, string]

export interface HydroServerOIDCOptions {
  clientId?: string
  redirectPath?: string
  postLogoutRedirectPath?: string
  accountHandoffPath?: string
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
  readonly authBase: string
  readonly etlBase: string
  readonly oidc: Required<HydroServerOIDCOptions>

  private _workspaces?: WorkspaceService
  private _things?: ThingService
  private _observedProperties?: ObservedPropertyService
  private _units?: UnitService
  private _processingLevels?: ProcessingLevelService
  private _resultQualifiers?: ResultQualifierService
  private _sensors?: SensorService
  private _datastreams?: DatastreamService
  private _orchestrationSystems?: OrchestrationSystemService
  private _session?: SessionService
  private _user?: UserService

  private _dataConnections?: DataConnectionService
  private _tasks?: TaskService
  private _thingFileAttachments?: ThingFileAttachmentService

  constructor(opts: HydroServerOptions) {
    const { host, oidc } = opts
    this.host = host.trim().replace(/\/+$/, '')
    this.resolvedHost = this.host || globalThis.location?.origin || ''
    this.baseRoute = `${this.host}/api/data`
    this.authBase = `${this.host}/api/auth`
    this.etlBase = `${this.host}/api/etl`
    this.oidc = {
      clientId: oidc?.clientId ?? 'hydroserver-data-management',
      redirectPath: oidc?.redirectPath ?? '/callback',
      postLogoutRedirectPath: oidc?.postLogoutRedirectPath ?? '/',
      accountHandoffPath: oidc?.accountHandoffPath ?? '/auth/handoff',
      scope: oidc?.scope ?? 'openid profile email',
    }
  }

  static async initialize(options: HydroServerOptions): Promise<HydroServer> {
    const client = new HydroServer(options)
    await client.session.initialize()
    return client
  }

  private listeners: Record<string, Array<(...args: any[]) => void>> = {}

  public on(eventName: string, callback: (...args: any[]) => void): void {
    ;(this.listeners[eventName] ??= []).push(callback)
  }

  public emit(eventName: string, ...args: any[]): void {
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
  get things(): ThingService {
    return (this._things ??= new ThingService(this))
  }
  get observedProperties(): ObservedPropertyService {
    return (this._observedProperties ??= new ObservedPropertyService(this))
  }
  get units(): UnitService {
    return (this._units ??= new UnitService(this))
  }
  get processingLevels(): ProcessingLevelService {
    return (this._processingLevels ??= new ProcessingLevelService(this))
  }
  get resultQualifiers(): ResultQualifierService {
    return (this._resultQualifiers ??= new ResultQualifierService(this))
  }
  get sensors(): SensorService {
    return (this._sensors ??= new SensorService(this))
  }
  get datastreams(): DatastreamService {
    return (this._datastreams ??= new DatastreamService(this))
  }
  get orchestrationSystems(): OrchestrationSystemService {
    return (this._orchestrationSystems ??= new OrchestrationSystemService(this))
  }
  get dataConnections(): DataConnectionService {
    return (this._dataConnections ??= new DataConnectionService(this))
  }
  get tasks(): TaskService {
    return (this._tasks ??= new TaskService(this))
  }
  get thingFileAttachments(): ThingFileAttachmentService {
    return (this._thingFileAttachments ??= new ThingFileAttachmentService(this))
  }
  get session(): SessionService {
    return (this._session ??= new SessionService(this))
  }
  get user(): UserService {
    return (this._user ??= new UserService(this))
  }
}
