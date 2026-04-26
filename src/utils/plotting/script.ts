/**
 * QC History Script — save / load.
 *
 * See `docs/HISTORY_SCRIPT.md` for the full design rationale. The
 * short version:
 *
 *   - **Save:** walk `record.history`, strip runtime-only fields
 *     (`isLoading`, `duration`, `executionMode`, `selected`), keep
 *     `method`, `args`, and the optional `status` flag. Wrap with
 *     a `version`, `createdAt`, and the wall-clock `window` the
 *     consumer was working in.
 *
 *   - **Load:** reset `history` + `redoStack`, `record.reload()`,
 *     then `record.dispatch(operations.map(o => [o.method, ...o.args]))`.
 *     Per-op failures are caught (the dispatch's own `catch` already
 *     marks the entry `status: "failed"`); we tally them in the
 *     returned `ApplyScriptReport` for the consumer to surface.
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
  ApplyScriptReport,
  EnumEditOperations,
  EnumFilterOperations,
  QcScript,
  QcScriptOperation,
  QcScriptWindow,
} from "../../types";
import { ObservationRecord } from "./observation-record";

/** The schema version this loader / serializer understands. */
export const QC_SCRIPT_VERSION = "1" as const;

const ALL_METHODS = new Set<string>([
  ...Object.values(EnumEditOperations),
  ...Object.values(EnumFilterOperations),
]);

/**
 * Serialize an `ObservationRecord`'s history into a `QcScript`.
 *
 * @param record  The record whose `.history` to serialize.
 * @param window  Wall-clock bounds the consumer was working in. The
 *   loader on the other end will fetch this range into the target
 *   record before replaying.
 */
export function serializeHistory(
  record: ObservationRecord,
  window: QcScriptWindow
): QcScript {
  const operations: QcScriptOperation[] = record.history.map((h) => {
    const op: QcScriptOperation = {
      method: h.method,
      args: h.args ? [...h.args] : [],
    };
    if (h.status === "failed") op.status = "failed";
    return op;
  });

  return {
    version: QC_SCRIPT_VERSION,
    createdAt: new Date().toISOString(),
    window: {
      startDate: window.startDate,
      endDate: window.endDate,
    },
    operations,
  };
}

/**
 * Parse and validate a JSON-decoded payload as a `QcScript`. Throws
 * on schema violations — callers should wrap in try/catch and
 * surface the message to the user. Validation is deliberately
 * minimal: structural shape, version, and per-op method recognition.
 * Arg shape per method is the dispatcher's job.
 */
export function parseScript(json: unknown): QcScript {
  if (!json || typeof json !== "object") {
    throw new Error("QC script must be a JSON object.");
  }
  const obj = json as Record<string, unknown>;

  if (obj.version !== QC_SCRIPT_VERSION) {
    throw new Error(
      `Unsupported QC script version: ${String(obj.version)}. ` +
      `This loader understands version "${QC_SCRIPT_VERSION}".`
    );
  }

  if (typeof obj.createdAt !== "string") {
    throw new Error("QC script is missing `createdAt` (ISO-8601 string).");
  }

  const w = obj.window as Record<string, unknown> | undefined;
  if (!w || typeof w !== "object") {
    throw new Error("QC script is missing `window`.");
  }
  if (typeof w.startDate !== "string" || typeof w.endDate !== "string") {
    throw new Error("`window.startDate` and `window.endDate` must be ISO-8601 strings.");
  }

  if (!Array.isArray(obj.operations)) {
    throw new Error("QC script `operations` must be an array.");
  }

  const operations: QcScriptOperation[] = obj.operations.map((raw, i) => {
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
    const op: QcScriptOperation = {
      method: o.method as EnumEditOperations | EnumFilterOperations,
      args: [...o.args],
    };
    if (o.status === "failed") op.status = "failed";
    return op;
  });

  return {
    version: QC_SCRIPT_VERSION,
    createdAt: obj.createdAt,
    window: {
      startDate: w.startDate,
      endDate: w.endDate,
    },
    operations,
  };
}

/**
 * Apply a parsed `QcScript` to a freshly-prepared `ObservationRecord`.
 *
 * Caller's responsibility BEFORE this runs:
 *   1. Pick the target datastream (no id matching is enforced — see
 *      the design doc's "Stay reusable" goal).
 *   2. Fetch the script's `window` into the record's raw data.
 *
 * What `applyScript` does:
 *   1. Resets `history` + `redoStack` in-place (preserves the array
 *      reference so the consumer's reactive ref stays bound).
 *   2. `await record.reload()` to restore from raw.
 *   3. Dispatches operations one at a time so per-op failures can be
 *      caught and reported. Failures don't abort the remainder.
 *
 * Returns an `ApplyScriptReport` summarising the outcome. Per-op
 * `HistoryItem.status` is also written by the dispatch path itself,
 * so the UI can read failures directly off the history entries.
 */
export async function applyScript(
  record: ObservationRecord,
  script: QcScript
): Promise<ApplyScriptReport> {
  // In-place clear so any consumer-side ref pointing at the array
  // (the qc-app's `editHistory` Pinia ref) stays connected.
  record.history.length = 0;
  record.redoStack.length = 0;
  await record.reload();

  const report: ApplyScriptReport = { applied: 0, failed: [] };

  for (let i = 0; i < script.operations.length; i++) {
    const op = script.operations[i];
    try {
      // dispatch handles routing to dispatchAction / dispatchFilter
      // based on whether the method is in EnumFilterOperations.
      await record.dispatch(op.method, ...op.args);
      // The dispatch path's catch block writes
      // `historyItem.status = "failed"` on throw. Read it back to
      // decide whether to count as applied.
      const last = record.history[record.history.length - 1];
      if (last?.status === "failed") {
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
