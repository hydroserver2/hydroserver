export type DataPoint = {
  date: Date
  value: number
}

export type DataArray = [string, number][]

export class ObservationRecord {
  dataArray: DataArray
  beginTime: string
  endTime: string
  loading: boolean

  constructor() {
    this.dataArray = []
    this.beginTime = ''
    this.endTime = ''
    this.loading = false
  }
}

export interface GraphSeries {
  id: string
  name: string
  data: DataPoint[]
  yAxisLabel: string
  lineColor: string
}

export type TimeSpacingUnit = 'seconds' | 'minutes' | 'hours' | 'days'

export type Tags = Record<string, string>

export function getTagValue(tags: Tags, key: string): string | undefined {
  return Object.hasOwn(tags, key) ? tags[key] : undefined
}

export type Frequency = 'daily' | 'weekly' | 'monthly' | null

export class HydroShareArchive {
  id: string
  monitoringSiteId: string
  link: string
  frequency: Frequency
  path: string
  datastreamIds: string[]
  publicResource: boolean

  constructor() {
    this.id = ''
    this.monitoringSiteId = ''
    this.link = ''
    this.frequency = null
    this.path = 'HydroShare'
    this.datastreamIds = []
    this.publicResource = false
  }
}

export class PostHydroShareArchive extends HydroShareArchive {
  resourceTitle?: string
  resourceAbstract?: string
  resourceKeywords?: string[]

  constructor() {
    super()
    this.resourceTitle = undefined
    this.resourceAbstract = undefined
    this.resourceKeywords = undefined
  }
}

export class MonitoringSite {
  id: string
  workspaceId: string
  name: string
  tags: Tags
  hydroShareArchive?: HydroShareArchive | null
  type: string
  code: string
  latitude?: number | ''
  longitude?: number | ''
  elevation_m?: number | ''
  elevationDatum: string
  adminArea1: string
  adminArea2: string
  country: string
  isPrivate: boolean
  description: string
  dataDisclaimer: string

  constructor() {
    this.id = ''
    this.workspaceId = ''
    this.name = ''
    this.tags = {}
    this.type = ''
    this.code = ''
    this.elevationDatum = 'WGS84'
    this.adminArea1 = ''
    this.adminArea2 = ''
    this.country = ''
    this.isPrivate = false
    this.description = ''
    this.dataDisclaimer = ''
  }
}

export class Datastream {
  id: string
  workspaceId: string
  name: string
  description: string
  monitoringSiteId: string
  observationType: string
  resultType?: string
  status?: string
  sampledMedium: string
  noDataValue: number
  aggregationStatistic: string
  unitId: string
  observedPropertyId: string
  methodId: string
  processingLevelId: string
  isPrivate: boolean
  isVisible: boolean
  phenomenonBeginTime?: string | null
  phenomenonEndTime?: string | null
  intendedTimeSpacing?: number
  intendedTimeSpacingUnit?: TimeSpacingUnit | null
  timeAggregationInterval: number | null
  timeAggregationIntervalUnit: TimeSpacingUnit
  valueCount: number
  tags: Tags

  constructor(monitoringSiteId?: string) {
    this.id = ''
    this.workspaceId = ''
    this.name = ''
    this.description = ''
    this.monitoringSiteId = monitoringSiteId || ''
    this.observationType = 'OM_Measurement'
    this.resultType = 'Time Series Coverage'
    this.sampledMedium = ''
    this.noDataValue = -9999
    this.aggregationStatistic = ''
    this.unitId = ''
    this.observedPropertyId = ''
    this.methodId = ''
    this.processingLevelId = ''
    this.timeAggregationInterval = null
    this.timeAggregationIntervalUnit = 'seconds'
    this.isPrivate = true
    this.isVisible = true
    this.valueCount = 0
    this.tags = {}
  }
}

export interface DatastreamExtended {
  id: string
  name: string
  description: string
  observationType: string
  resultType?: string
  status?: string
  sampledMedium: string
  noDataValue: number
  aggregationStatistic: string
  isPrivate: boolean
  isVisible: boolean
  phenomenonBeginTime?: string | null
  phenomenonEndTime?: string | null
  intendedTimeSpacing?: number
  intendedTimeSpacingUnit?: TimeSpacingUnit | null
  timeAggregationInterval: number | null
  timeAggregationIntervalUnit: TimeSpacingUnit
  valueCount: number

  monitoringSite: MonitoringSite
  workspace: Workspace
  unit: Unit
  observedProperty: ObservedProperty
  method: Method
  processingLevel: ProcessingLevel
}

export class Unit {
  id: string
  workspaceId: string
  name: string
  symbol: string
  definition: string
  type: string

  constructor() {
    this.id = ''
    this.workspaceId = ''
    this.name = ''
    this.symbol = ''
    this.definition = ''
    this.type = ''
  }
}

export class Method {
  id: string
  workspaceId: string
  name: string
  description: string
  code: string
  type: string
  definition: string
  sensorModel: string
  sensorModelManufacturer: string
  sensorModelDefinition: string

  constructor() {
    this.id = ''
    this.workspaceId = ''
    this.name = ''
    this.description = ''
    this.code = ''
    this.type = 'Instrument Deployment'
    this.definition = ''
    this.sensorModel = ''
    this.sensorModelManufacturer = ''
    this.sensorModelDefinition = ''
  }
}

export class ObservedProperty {
  id: string
  workspaceId: string
  name: string
  definition: string
  description: string
  type: string
  code: string

  constructor() {
    this.id = ''
    this.workspaceId = ''
    this.name = ''
    this.definition = ''
    this.description = ''
    this.type = 'Hydrology'
    this.code = ''
  }
}

export class ProcessingLevel {
  id: string
  workspaceId: string
  code: string
  name: string
  description: string
  definition: string

  constructor() {
    this.id = ''
    this.workspaceId = ''
    this.code = ''
    this.name = ''
    this.description = ''
    this.definition = ''
  }
}

export class ResultQualifier {
  id: string
  workspaceId: string
  code: string
  description: string

  constructor() {
    this.id = ''
    this.workspaceId = ''
    this.code = ''
    this.description = ''
  }
}

export class Organization {
  name?: string
  code?: string
  type?: string
  description?: string
  link?: string

  constructor() {}
}

export class User {
  id: string
  email: string
  password: string
  firstName: string
  middleName: string
  lastName: string
  phone: string
  address: string
  organization?: Organization | null
  type: string
  link: string
  accountType: 'admin' | 'standard' | 'limited'
  hydroShareConnected: boolean

  constructor() {
    this.id = ''
    this.email = ''
    this.password = ''
    this.firstName = ''
    this.middleName = ''
    this.lastName = ''
    this.phone = ''
    this.address = ''
    this.type = ''
    this.link = ''
    this.accountType = 'standard'
    this.hydroShareConnected = false
  }
}

export interface LinkedResource {
  id: string
  name: string
  description?: string | null
  type: string
  link: string
}

export class OAuthProvider {
  id: string
  name: string
  iconLink: string
  signupEnabled: boolean
  connectEnabled: boolean

  constructor() {
    this.id = ''
    this.name = ''
    this.iconLink = ''
    this.signupEnabled = true
    this.connectEnabled = true
  }
}

export enum PermissionAction {
  View = 'view',
  Create = 'create',
  Edit = 'edit',
  Delete = 'delete',
}

export enum PermissionResource {
  Global = '*',
  Workspace = 'Workspace',
  Role = 'Role',
  ServiceAccount = 'ServiceAccount',
  Collaborator = 'Collaborator',
  MonitoringSite = 'MonitoringSite',
  ObservedProperty = 'ObservedProperty',
  ProcessingLevel = 'ProcessingLevel',
  ResultQualifier = 'ResultQualifier',
  Method = 'Method',
  Unit = 'Unit',
  Datastream = 'Datastream',
  Observation = 'Observation',
  DataConnection = 'DataConnection',
  EtlTask = 'EtlTask',
  RatingCurve = 'RatingCurve',
  DataProductTask = 'DataProductTask',
  MonitoringTask = 'MonitoringTask',
}

export interface Permission {
  action: PermissionAction
  resource: PermissionResource
}

export interface CollaboratorRole {
  name: string
  description: string
  id: string
  workspaceId: string
  permissions: Permission[]
}

export interface ServiceAccountContact {
  id: string
  name: string
  email: string
}

export class ServiceAccount {
  id = ''
  key = ''
  email = ''
  name = ''
  description = ''
  isActive = true
  keyExpiresAt = ''
  createdAt = ''
  lastUsedAt = ''
  workspaceId = ''

  constructor(init?: Partial<ServiceAccount>) {
    Object.assign(this, init)
  }
}

export interface WorkspaceData {
  id: string
  name: string
  isPrivate: boolean
  owner: User
  collaboratorRole: CollaboratorRole
  pendingTransferTo?: User | null
}

export class Workspace {
  id: string
  name: string
  isPrivate: boolean
  owner: UserInfo | null
  collaboratorRole: CollaboratorRole | null
  pendingTransferTo?: UserInfo | null

  constructor() {
    this.id = ''
    this.name = ''
    this.isPrivate = false
    this.owner = null
    this.collaboratorRole = null
    this.pendingTransferTo = null
  }
}

export interface UserInfo {
  name: string
  email: string
  phone: string
  address: string
  link: string
  type: string
  organizationName: string
}

export interface MonitoringSiteMarker {
  id: string
  workspaceId: string
  name: string
  type: string
  isPrivate: boolean
  latitude: number
  longitude: number
}

export interface SiteTypeIcon {
  icon: string
  siteTypes: string[]
}

export interface MonitoringSiteMapSummary extends MonitoringSiteMarker {
  code: string
  tags: Tags
}

export interface MonitoringSiteTaskSummary {
  id: string
  name: string
  type: string
  productTaskCount: number
  productTaskAttentionCount: number
  monitoringTaskCount: number
  monitoringTaskAttentionCount: number
}

export class Collaborator {
  user: UserInfo | null
  serviceAccount: ServiceAccountContact | null
  role: CollaboratorRole

  constructor() {
    this.user = null
    this.serviceAccount = null
    this.role = {
      name: '',
      description: '',
      id: '',
      workspaceId: '',
      permissions: [],
    }
  }
}
