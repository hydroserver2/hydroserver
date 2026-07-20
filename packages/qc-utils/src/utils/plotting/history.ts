/**
 * QC History — save / load.
 *
 * See `docs/QC_HISTORY.md` for the full design rationale. The
 * short version:
 *
 *   - **Save:** walk `record.history`, keep `method` and `args`,
 *     project the live `HistoryExecution` into a `QcHistoryExecution`
 *     (drop `inFlight` since a serialized entry is always
 *     resolved; keep the rest — `startedAt`, `status`, `durationMs`,
 *     `mode`, `datasetSize`, `selectionSize`). The runtime-only
 *     `selected` array is recomputed on replay and not persisted.
 *     Wrap with a `version`, `createdAt`, and the wall-clock
 *     `window` the consumer was working in.
 *
 *   - **Load:** reset `history` + `redoStack`, `record.reload()`,
 *     then `record.dispatch(operations.map(o => [o.method, ...o.args]))`.
 *     Per-op failures are caught (the dispatch's own `catch` already
 *     marks the entry `status: "failed"`); we tally them in the
 *     returned `ApplyHistoryReport` for the consumer to surface.
 *
 *   - **No per-method serialization rules.** Args round-trip
 *     verbatim. Selection-coupled ops (DELETE_POINTS, INTERPOLATE,
 *     SHIFT_DATETIMES, DRIFT_CORRECTION, CHANGE_VALUES,
 *     ASSIGN_*_BULK) read their target indices off
 *     `history[length - 2].selected` at runtime — replay walks the
 *     ops in order so the SELECTION is in the right slot when the
 *     consumer fires.
 */

import {
  ApplyHistoryReport,
  EnumEditOperations,
  EnumFilterOperations,
  QcHistory,
  QcHistoryExecution,
  QcHistoryOperation,
  QcHistoryWindow,
} from "../../types";
import { ObservationRecord } from "./observation-record";

/** The schema version this loader / serializer understands. */
export const QC_HISTORY_VERSION = "1" as const;

const ALL_METHODS = new Set<string>([
  ...Object.values(EnumEditOperations),
  ...Object.values(EnumFilterOperations),
]);

/**
 * Project a runtime `HistoryExecution` into the serialized
 * `QcHistoryExecution` shape, dropping `inFlight` (always false in a
 * resolved entry) and rejecting non-finite numeric values so a
 * round-tripped QC history can't poison the schema. Returns `undefined`
 * when the resulting projection would be empty, so callers can skip
 * the field entirely on the wire instead of emitting `{}`.
 */
function projectExecution(
  exec: import("../../types").HistoryExecution | undefined,
): QcHistoryExecution | undefined {
  if (!exec) return undefined;
  const out: QcHistoryExecution = {};
  const num = (v: unknown): number | undefined =>
    typeof v === "number" && Number.isFinite(v) ? v : undefined;
  const startedAt = num(exec.startedAt);
  if (startedAt !== undefined) out.startedAt = startedAt;
  if (exec.status === "success" || exec.status === "failed") out.status = exec.status;
  const durationMs = num(exec.durationMs);
  if (durationMs !== undefined) out.durationMs = durationMs;
  if (exec.mode === "worker" || exec.mode === "inline") out.mode = exec.mode;
  const datasetSize = num(exec.datasetSize);
  if (datasetSize !== undefined) out.datasetSize = datasetSize;
  const selectionSize = num(exec.selectionSize);
  if (selectionSize !== undefined) out.selectionSize = selectionSize;
  return Object.keys(out).length === 0 ? undefined : out;
}

/**
 * Parse the optional `execution` field from a per-op JSON entry.
 * Each field is independently typed-narrowed; malformed values
 * throw a single descriptive error so the caller can surface the
 * exact field that drifted. Returns `undefined` when the field is
 * absent so backward-compatibility with pre-execution histories is
 * preserved.
 */
function parseExecution(
  raw: unknown,
  index: number,
): QcHistoryExecution | undefined {
  if (raw === undefined) return undefined;
  if (!raw || typeof raw !== "object") {
    throw new Error(`Operation ${index} \`execution\` must be an object when present.`);
  }
  const o = raw as Record<string, unknown>;
  const out: QcHistoryExecution = {};
  const assertFiniteNumber = (field: string, value: unknown) => {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new Error(
        `Operation ${index} \`execution.${field}\` must be a finite number when present.`
      );
    }
  };
  if (o.startedAt !== undefined) {
    assertFiniteNumber("startedAt", o.startedAt);
    out.startedAt = o.startedAt as number;
  }
  if (o.status !== undefined) {
    if (o.status !== "success" && o.status !== "failed") {
      throw new Error(
        `Operation ${index} \`execution.status\` must be "success" or "failed" when present.`
      );
    }
    out.status = o.status;
  }
  if (o.durationMs !== undefined) {
    assertFiniteNumber("durationMs", o.durationMs);
    out.durationMs = o.durationMs as number;
  }
  if (o.mode !== undefined) {
    if (o.mode !== "worker" && o.mode !== "inline") {
      throw new Error(
        `Operation ${index} \`execution.mode\` must be "worker" or "inline" when present.`
      );
    }
    out.mode = o.mode;
  }
  if (o.datasetSize !== undefined) {
    assertFiniteNumber("datasetSize", o.datasetSize);
    out.datasetSize = o.datasetSize as number;
  }
  if (o.selectionSize !== undefined) {
    assertFiniteNumber("selectionSize", o.selectionSize);
    out.selectionSize = o.selectionSize as number;
  }
  return out;
}

/**
 * Serialize an `ObservationRecord`'s history into a `QcHistory`.
 *
 * @param record  The record whose `.history` to serialize.
 * @param window  Wall-clock bounds the consumer was working in. The
 *   loader on the other end will fetch this range into the target
 *   record before replaying.
 */
export function serializeHistory(
  record: ObservationRecord,
  window: QcHistoryWindow
): QcHistory {
  const operations: QcHistoryOperation[] = record.history.map((h) => {
    const op: QcHistoryOperation = {
      method: h.method,
      args: h.args ? [...h.args] : [],
    };
    const exec = projectExecution(h.execution);
    if (exec) op.execution = exec;
    return op;
  });

  return {
    version: QC_HISTORY_VERSION,
    createdAt: new Date().toISOString(),
    window: {
      startDate: window.startDate,
      endDate: window.endDate,
    },
    operations,
  };
}

/**
 * Parse and validate a JSON-decoded payload as a `QcHistory`. Throws
 * on schema violations — callers should wrap in try/catch and
 * surface the message to the user. Validation is deliberately
 * minimal: structural shape, version, and per-op method recognition.
 * Arg shape per method is the dispatcher's job.
 */
export function parseHistory(json: unknown): QcHistory {
  if (!json || typeof json !== "object") {
    throw new Error("QC history must be a JSON object.");
  }
  const obj = json as Record<string, unknown>;

  if (obj.version !== QC_HISTORY_VERSION) {
    throw new Error(
      `Unsupported QC history version: ${String(obj.version)}. ` +
      `This loader understands version "${QC_HISTORY_VERSION}".`
    );
  }

  if (typeof obj.createdAt !== "string") {
    throw new Error("QC history is missing `createdAt` (ISO-8601 string).");
  }

  const w = obj.window as Record<string, unknown> | undefined;
  if (!w || typeof w !== "object") {
    throw new Error("QC history is missing `window`.");
  }
  if (typeof w.startDate !== "string" || typeof w.endDate !== "string") {
    throw new Error("`window.startDate` and `window.endDate` must be ISO-8601 strings.");
  }

  if (!Array.isArray(obj.operations)) {
    throw new Error("QC history `operations` must be an array.");
  }

  const operations: QcHistoryOperation[] = obj.operations.map((raw, i) => {
    if (!raw || typeof raw !== "object") {
      throw new Error(`Operation ${i} must be an object.`);
    }
    const o = raw as Record<string, unknown>;
    if (typeof o.method !== "string") {
      throw new Error(`Operation ${i} missing string \`method\`.`);
    }
    if (!ALL_METHODS.has(o.method)) {
      throw new Error(`Operation ${i} has unknown method: "${o.method}".`);
    }
    if (!Array.isArray(o.args)) {
      throw new Error(`Operation ${i} \`args\` must be an array.`);
    }
    const op: QcHistoryOperation = {
      method: o.method as EnumEditOperations | EnumFilterOperations,
      args: [...o.args],
    };
    const exec = parseExecution(o.execution, i);
    if (exec) op.execution = exec;
    return op;
  });

  return {
    version: QC_HISTORY_VERSION,
    createdAt: obj.createdAt,
    window: {
      startDate: w.startDate,
      endDate: w.endDate,
    },
    operations,
  };
}

/**
 * Apply a parsed `QcHistory` to a freshly-prepared `ObservationRecord`.
 *
 * Caller's responsibility BEFORE this runs:
 *   1. Pick the target datastream (no id matching is enforced — see
 *      the design doc's "Stay reusable" goal).
 *   2. Fetch the QC history's `window` into the record's raw data.
 *
 * What `applyHistory` does:
 *   1. Resets `history` + `redoStack` in-place (preserves the array
 *      reference so the consumer's reactive ref stays bound).
 *   2. `await record.reload()` to restore from raw.
 *   3. Dispatches operations one at a time so per-op failures can be
 *      caught and reported. Failures don't abort the remainder.
 *
 * Returns an `ApplyHistoryReport` summarising the outcome. Per-op
 * `HistoryItem.status` is also written by the dispatch path itself,
 * so the UI can read failures directly off the history entries.
 */
export async function applyHistory(
  record: ObservationRecord,
  history: QcHistory
): Promise<ApplyHistoryReport> {
  // In-place clear so any consumer-side ref pointing at the array
  // (the qc-app's `editHistory` Pinia ref) stays connected.
  record.history.length = 0;
  record.redoStack.length = 0;
  await record.reload();

  const report: ApplyHistoryReport = { applied: 0, failed: [] };

  for (let i = 0; i < history.operations.length; i++) {
    const op = history.operations[i];
    try {
      // dispatch handles routing to dispatchAction / dispatchFilter
      // based on whether the method is in EnumFilterOperations.
      await record.dispatch(op.method, ...op.args);
      // The dispatch path's catch block writes
      // `historyItem.execution.status = "failed"` on throw. Read it
      // back to decide whether to count as applied.
      const last = record.history[record.history.length - 1];
      if (last?.execution.status === "failed") {
        report.failed.push({
          index: i,
          method: op.method,
          error: "Operation handler reported failure (see console).",
        });
      } else {
        report.applied++;
      }
    } catch (e) {
      // Defensive: dispatch should swallow handler errors itself,
      // but if it ever throws we still want to record + continue.
      report.failed.push({
        index: i,
        method: op.method,
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }

  return report;
}
