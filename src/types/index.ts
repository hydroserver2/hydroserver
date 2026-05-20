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
  /**
   * Single-operation assignment of distinct values at distinct indices.
   * Args: `(indices: number[], values: number[])` — parallel arrays where
   * `values[i]` is written to `dataY[indices[i]]`. No workers, no per-row
   * ceremony. Intended for table-driven edits.
   */
  ASSIGN_VALUES_BULK = "ASSIGN_VALUES_BULK",
  DELETE_POINTS = "DELETE_POINTS",
  DRIFT_CORRECTION = "DRIFT_CORRECTION",
  INTERPOLATE = "INTERPOLATE",
  SHIFT_DATETIMES = "SHIFT_DATETIMES",
  /**
   * Single-operation assignment of distinct datetimes at distinct indices.
   * Args: `(indices: number[], datetimes: number[])` — parallel arrays of
   * epoch-milliseconds. Runs one combined delete + add under the hood.
   */
  ASSIGN_DATETIMES_BULK = "ASSIGN_DATETIMES_BULK",
  FILL_GAPS = "FILL_GAPS",
}

export enum EnumFilterOperations {
  FIND_GAPS = "FIND_GAPS",
  PERSISTENCE = "PERSISTENCE",
  CHANGE = "CHANGE",
  RATE_OF_CHANGE = "RATE_OF_CHANGE",
  VALUE_THRESHOLD = "VALUE_THRESHOLD",
  DATETIME_RANGE = "DATETIME_RANGE",
  SELECTION = "SELECTION",
}

export enum FilterOperation {
  LT = "Less than",
  LTE = "Less than or equal to",
  GT = "Greater than",
  GTE = "Greater than or equal to",
  E = "Equal",
}

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

/**
 * Per-dispatch runtime information attached to every `HistoryItem`.
 *
 * Populated in two phases by `ObservationRecord.dispatchAction` /
 * `dispatchFilter`:
 *
 *   - **Push time**: `startedAt`, `inFlight: true`, `datasetSize`,
 *     and (for selection-consuming edits) `selectionSize` are set
 *     before the handler runs.
 *   - **Resolve time**: `status`, `durationMs`, `mode`, and (for
 *     filters) `selectionSize` are set when the handler returns or
 *     throws.
 *
 * The qc-app reads this object to drive the EditHistory UI
 * (per-row spinner via `inFlight`, failure badge via `status`,
 * duration text via `durationMs`, dev-only worker/inline chip via
 * `mode`). Replays from `undo()` / `redo()` / `applyScript` build
 * a fresh execution record for the new run rather than re-stamping
 * the saved one.
 */
export interface HistoryExecution {
  /**
   * Wall-clock epoch-milliseconds (UTC) when the dispatch site pushed
   * this entry. Re-stamped on every replay so the in-memory value
   * always reflects the current session's execution. `serializeHistory`
   * persists it for audit; the script loader does not restore it.
   */
  startedAt: number;
  /**
   * True from the moment the dispatch pushed the entry until the
   * handler resolves (success or failure). Drives per-row spinners
   * in the qc-app.
   */
  inFlight: boolean;
  /** Final outcome — `undefined` while `inFlight` is `true`. */
  status?: "success" | "failed";
  /**
   * Wall-clock duration in milliseconds. Set after the handler
   * resolves. `undefined` while `inFlight`.
   */
  durationMs?: number;
  /**
   * Whether the op actually ran on a web worker or inline on the
   * main thread. Populated based on the calibration decision and
   * any always-inline / always-worker handler behaviour. Mainly
   * useful in dev for verifying that the calibration layer is
   * routing as expected.
   */
  mode?: "worker" | "inline";
  /**
   * Number of observations in the record at the time the op ran,
   * captured at push time. Reflects the pre-edit shape — i.e.
   * exactly what the handler saw on entry. Useful for retrospective
   * perf inspection: "this op took 300ms because the record had
   * 500k points."
   */
  datasetSize?: number;
  /**
   * Number of indices the op acted on. For filters this is the
   * size of the resulting selection (populated at resolve time);
   * for selection-consuming edits it's the size of the preceding
   * SELECTION (populated at push time). `undefined` when not
   * applicable (e.g. ADD_POINTS, which is datetime-addressed).
   */
  selectionSize?: number;
}

export type HistoryItem = {
  method: EnumEditOperations | EnumFilterOperations;
  args?: any[];
  selected?: number[];
  /**
   * Per-dispatch runtime information. Always present; some fields
   * populate at push time, others fill in after the handler resolves.
   * See `HistoryExecution` for the two-phase population rules.
   */
  execution: HistoryExecution;
};

// --- QC History Script (save / load format) ----------------------
// See `docs/HISTORY_SCRIPT.md` for the full design rationale.

/** The wall-clock window the script was authored against. The
 *  loader is responsible for fetching this exact range of
 *  observations into the target `ObservationRecord` before
 *  replaying. ISO-8601 strings (not `Date`) so the type round-trips
 *  cleanly through `JSON.stringify`/`JSON.parse`. */
export type QcScriptWindow = {
  startDate: string;
  endDate: string;
};

/**
 * The execution record persisted alongside a saved script operation.
 * Mirrors `HistoryExecution` minus the runtime-only `inFlight` flag,
 * since a serialized op is always "resolved" by definition. Every
 * field is optional so pre-v1.1 scripts (and any consumer that
 * hand-writes the JSON) still load.
 *
 * Replays do **not** restore these values onto the new
 * `HistoryItem.execution`; the dispatch site stamps fresh runtime
 * data for the current session. Persistence is for audit only:
 * "this op originally ran inline on a 50k record in 240ms."
 */
export type QcScriptExecution = {
  startedAt?: number;
  status?: "success" | "failed";
  durationMs?: number;
  mode?: "worker" | "inline";
  datasetSize?: number;
  selectionSize?: number;
};

/** A single replayable operation entry. Mirrors the
 *  `[method, ...args]` tuple shape that
 *  `ObservationRecord.dispatch` accepts. `execution` carries
 *  per-dispatch audit data (timing, mode, dataset shape) round-
 *  tripped verbatim so the saved script preserves the authoring
 *  context for review. */
export type QcScriptOperation = {
  method: EnumEditOperations | EnumFilterOperations;
  args: any[];
  execution?: QcScriptExecution;
};

/** A serialized QC history. Schema `version: "1"`. */
export type QcScript = {
  version: "1";
  createdAt: string;
  window: QcScriptWindow;
  operations: QcScriptOperation[];
};

/** Returned by `applyScript` — per-op success/failure tally. */
export type ApplyScriptReport = {
  applied: number;
  failed: Array<{ index: number; method: string; error: string }>;
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
