import { DataSource } from "@/models";
import { ObservationRecord } from "@/utils/plotting/observation-record";

export type EnumDictionary<T extends string | symbol | number, U> = {
  [K in T]: U;
};

export enum TimeUnit {
  SECOND = "s",
  MINUTE = "m",
  HOUR = "h",
  DAY = "D",
  WEEK = "W",
  MONTH = "M",
  YEAR = "Y",
}

export enum EnumEditOperations {
  ADD_POINTS = "ADD_POINTS",
  CHANGE_VALUES = "CHANGE_VALUES",
  DELETE_POINTS = "DELETE_POINTS",
  DRIFT_CORRECTION = "DRIFT_CORRECTION",
  INTERPOLATE = "INTERPOLATE",
  SHIFT_DATETIMES = "SHIFT_DATETIMES",
  FILL_GAPS = "FILL_GAPS",
}

export enum EnumFilterOperations {
  FIND_GAPS = "FIND_GAPS",
  PERSISTENCE = "PERSISTENCE",
  CHANGE = "CHANGE",
  RATE_OF_CHANGE = "RATE_OF_CHANGE",
  VALUE_THRESHOLD = "VALUE_THRESHOLD",
  SELECTION = "SELECTION",
}

export enum FilterOperation {
  LT = "Less than",
  LTE = "Less than or equal to",
  GT = "Greater than",
  GTE = "Greater than or equal to",
  E = "Equal",
  START = "Start datetime",
  END = "End datetime",
}

export const FilterOperationFn: EnumDictionary<
  FilterOperation,
  (value: number, toCompare: number) => boolean
> = {
  [FilterOperation.LT]: (value: number, toCompare: number) => {
    return value < toCompare;
  },
  [FilterOperation.LTE]: (value: number, toCompare: number) => {
    return value <= toCompare;
  },
  [FilterOperation.GT]: (value: number, toCompare: number) => {
    return value > toCompare;
  },
  [FilterOperation.GTE]: (value: number, toCompare: number) => {
    return value >= toCompare;
  },
  [FilterOperation.E]: (value: number, toCompare: number) => {
    return value == toCompare;
  },
  [FilterOperation.START]: (value: number, toCompare: number) => {
    return value == toCompare;
  },
  [FilterOperation.END]: (value: number, toCompare: number) => {
    return value == toCompare;
  },
};

export enum Operator {
  ADD = "ADD",
  SUB = "SUB",
  MULT = "MULT",
  DIV = "DIV",
  ASSIGN = "ASSIGN",
}

export enum LogicalOperation {
  LT = "Less than",
  LTE = "Less than or equal to",
  GT = "Greater than",
  GTE = "Greater than or equal to",
  E = "Equal",
}

export const LogicalComparator: EnumDictionary<
  LogicalOperation,
  (value: number, toCompare: number) => boolean
> = {
  [LogicalOperation.LT]: (value: number, toCompare: number) => {
    return value < toCompare;
  },
  [LogicalOperation.LTE]: (value: number, toCompare: number) => {
    return value <= toCompare;
  },
  [LogicalOperation.GT]: (value: number, toCompare: number) => {
    return value > toCompare;
  },
  [LogicalOperation.GTE]: (value: number, toCompare: number) => {
    return value >= toCompare;
  },
  [LogicalOperation.E]: (value: number, toCompare: number) => {
    return value == toCompare;
  },
};

export type HistoryItem = {
  method: EnumEditOperations | EnumFilterOperations;
  icon: string;
  isLoading: boolean;
  args?: any[];
  duration?: number;
  selected?: number[];
  status?: "success" | "failed";
};

export type DataPoint = {
  date: Date;
  value: number;
};

export type DataArray = [string, number][];

export interface GraphSeries {
  id: string;
  name: string;
  data: ObservationRecord;
  yAxisLabel: string;
  seriesOption: any;
}

export type TimeSpacingUnit = "seconds" | "minutes" | "hours" | "days";

export interface Tag {
  key: string;
  value: string;
}

export type Frequency = "daily" | "weekly" | "monthly" | null;

export class HydroShareArchive {
  id: string;
  thingId: string;
  link: string;
  frequency: Frequency;
  path: string;
  datastreamIds: string[];
  publicResource: boolean;

  constructor() {
    this.id = "";
    this.thingId = "";
    this.link = "";
    this.frequency = null;
    this.path = "HydroShare";
    this.datastreamIds = [];
    this.publicResource = false;
  }
}

export class PostHydroShareArchive extends HydroShareArchive {
  resourceTitle?: string;
  resourceAbstract?: string;
  resourceKeywords?: string[];

  constructor() {
    super();
    this.resourceTitle = undefined;
    this.resourceAbstract = undefined;
    this.resourceKeywords = undefined;
  }
}

export class Location {
  latitude?: number | "";
  longitude?: number | "";
  elevation_m?: number | "";
  elevationDatum: string;
  state: string;
  county: string;
  country: string;

  constructor() {
    this.elevationDatum = "WGS84";
    this.state = "";
    this.county = "";
    this.country = "";
  }
}

export class Thing {
  id: string;
  workspaceId: string;
  name: string;
  location: Location = new Location();
  tags: Tag[];
  hydroShareArchive?: HydroShareArchive | null;
  siteType: string;
  samplingFeatureCode: string;
  isPrivate: boolean;
  description: string;
  samplingFeatureType: string;
  dataDisclaimer: string;

  constructor() {
    this.id = "";
    this.workspaceId = "";
    this.name = "";
    this.tags = [];
    this.siteType = "";
    this.samplingFeatureCode = "";
    this.isPrivate = false;
    this.description = "";
    this.samplingFeatureType = "Site";
    this.dataDisclaimer = "";
  }
}

export interface ThingWithColor extends Thing {
  color?: {
    borderColor: string;
    background: string;
    glyphColor: string;
  };
  tagValue?: string;
}

export class Datastream {
  id: string;
  workspaceId: string;
  name: string;
  description: string;
  thingId: string;
  observationType: string;
  resultType?: string;
  status?: string;
  sampledMedium: string;
  noDataValue: number;
  aggregationStatistic: string;
  unitId: string;
  observedPropertyId: string;
  sensorId: string;
  processingLevelId: string;
  isPrivate: boolean;
  isVisible: boolean;
  phenomenonBeginTime?: string | null;
  phenomenonEndTime?: string | null;
  intendedTimeSpacing?: number;
  intendedTimeSpacingUnit?: TimeSpacingUnit | null;
  timeAggregationInterval: number | null;
  timeAggregationIntervalUnit: TimeSpacingUnit;
  dataSourceId?: string | null;
  valueCount: number;

  constructor(thingId?: string) {
    this.id = "";
    this.workspaceId = "";
    this.name = "";
    this.description = "";
    this.thingId = thingId || "";
    this.observationType = "OM_Measurement";
    this.resultType = "Time Series Coverage";
    this.sampledMedium = "";
    this.noDataValue = -9999;
    this.aggregationStatistic = "";
    this.unitId = "";
    this.observedPropertyId = "";
    this.sensorId = "";
    this.processingLevelId = "";
    this.timeAggregationInterval = null;
    this.timeAggregationIntervalUnit = "seconds";
    this.isPrivate = true;
    this.isVisible = true;
    this.valueCount = 0;
  }
}

export interface DatastreamExtended {
  id: string;
  name: string;
  description: string;
  observationType: string;
  resultType?: string;
  status?: string;
  sampledMedium: string;
  noDataValue: number;
  aggregationStatistic: string;
  isPrivate: boolean;
  isVisible: boolean;
  phenomenonBeginTime?: string | null;
  phenomenonEndTime?: string | null;
  intendedTimeSpacing?: number;
  intendedTimeSpacingUnit?: TimeSpacingUnit | null;
  timeAggregationInterval: number | null;
  timeAggregationIntervalUnit: TimeSpacingUnit;
  dataSourceId?: string | null;
  valueCount: number;

  thing: Thing;
  workspace: Workspace;
  unit: Unit;
  observedProperty: ObservedProperty;
  sensor: Sensor;
  processingLevel: ProcessingLevel;
  dataSource: DataSource;
}

export class Unit {
  id: string;
  workspaceId: string;
  name: string;
  symbol: string;
  definition: string;
  type: string;

  constructor() {
    this.id = "";
    this.workspaceId = "";
    this.name = "";
    this.symbol = "";
    this.definition = "";
    this.type = "";
  }
}

export class Sensor {
  id: string;
  workspaceId: string;
  name: string;
  description: string;
  manufacturer: string;
  model: string;
  methodType: string;
  methodCode: string;
  methodLink: string;
  encodingType: string;
  modelLink: string;

  constructor() {
    this.id = "";
    this.workspaceId = "";
    this.name = "";
    this.description = "";
    this.manufacturer = "";
    this.model = "";
    this.methodType = "Instrument Deployment";
    this.methodCode = "";
    this.methodLink = "";
    this.encodingType = "application/json";
    this.modelLink = "";
  }
}

export class ObservedProperty {
  id: string;
  workspaceId: string;
  name: string;
  definition: string;
  description: string;
  type: string;
  code: string;

  constructor() {
    this.id = "";
    this.workspaceId = "";
    this.name = "";
    this.definition = "";
    this.description = "";
    this.type = "Hydrology";
    this.code = "";
  }
}

export class ProcessingLevel {
  id: string;
  workspaceId: string;
  code: string;
  definition: string;
  explanation: string;

  constructor() {
    this.id = "";
    this.workspaceId = "";
    this.code = "";
    this.definition = "";
    this.explanation = "";
  }
}

export class ResultQualifier {
  id: string;
  workspaceId: string;
  code: string;
  description: string;

  constructor() {
    this.id = "";
    this.workspaceId = "";
    this.code = "";
    this.description = "";
  }
}

export class Organization {
  name?: string;
  code?: string;
  type?: string;
  description?: string;
  link?: string;

  constructor() { }
}

export class User {
  id: string;
  email: string;
  password: string;
  firstName: string;
  middleName: string;
  lastName: string;
  phone: string;
  address: string;
  organization?: Organization | null;
  type: string;
  link: string;
  accountType: "admin" | "standard" | "limited";
  hydroShareConnected: boolean;

  constructor() {
    this.id = "";
    this.email = "";
    this.password = "";
    this.firstName = "";
    this.middleName = "";
    this.lastName = "";
    this.phone = "";
    this.address = "";
    this.type = "";
    this.link = "";
    this.accountType = "standard";
    this.hydroShareConnected = false;
  }
}

export interface Photo {
  name: string;
  link: string;
}

export class OAuthProvider {
  id: string;
  name: string;
  iconLink: string;
  signupEnabled: boolean;
  connectEnabled: boolean;

  constructor() {
    this.id = "";
    this.name = "";
    this.iconLink = "";
    this.signupEnabled = true;
    this.connectEnabled = true;
  }
}

export enum PermissionAction {
  Global = "*",
  View = "view",
  Create = "create",
  Edit = "edit",
  Delete = "delete",
}

export enum PermissionResource {
  Global = "*",
  Workspace = "Workspace",
  Collaborator = "Collaborator",
  Thing = "Thing",
  Datastream = "Datastream",
  Sensor = "Sensor",
  Unit = "Unit",
  ObservedProperty = "ObservedProperty",
  ProcessingLevel = "ProcessingLevel",
  Observation = "Observation",
}

export interface Permission {
  action: PermissionAction;
  resource: PermissionResource;
}

export interface CollaboratorRole {
  name: string;
  description: string;
  id: string;
  workspaceId: string;
  isApikeyRole: boolean;
  isUserRole: boolean;
  permissions: Permission[];
}

export class ApiKey {
  id = "";
  key = "";
  name = "";
  description = "";
  isActive = true;
  expiresAt = "";
  createdAt = "";
  lastUsed = "";
  workspaceId = "";
  role: CollaboratorRole | null = null;

  constructor(init?: Partial<ApiKey>) {
    Object.assign(this, init);
  }
}

export interface WorkspaceData {
  id: string;
  name: string;
  isPrivate: boolean;
  owner: User;
  collaboratorRole: CollaboratorRole;
  pendingTransferTo?: User | null;
}

export class Workspace {
  id: string;
  name: string;
  isPrivate: boolean;
  owner: UserInfo | null;
  collaboratorRole: CollaboratorRole | null;
  pendingTransferTo?: UserInfo | null;

  constructor() {
    this.id = "";
    this.name = "";
    this.isPrivate = false;
    this.owner = null;
    this.collaboratorRole = null;
    this.pendingTransferTo = null;
  }
}

export interface UserInfo {
  name: string;
  email: string;
  phone: string;
  address: string;
  link: string;
  type: string;
  organizationName: string;
}

export class Collaborator {
  user: UserInfo;
  role: CollaboratorRole;

  constructor() {
    this.user = {
      phone: "",
      address: "",
      link: "",
      type: "",
      name: "",
      email: "",
      organizationName: "",
    };
    this.role = {
      name: "",
      description: "",
      id: "",
      isApikeyRole: false,
      isUserRole: false,
      workspaceId: "",
      permissions: [],
    };
  }
}

export interface ApiError {
  status: number;
  message?: string;
}
