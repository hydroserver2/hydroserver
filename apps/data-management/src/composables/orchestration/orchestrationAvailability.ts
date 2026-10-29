import { settings } from '@/config/settings'

export const ORCHESTRATION_DISABLED_TOOLTIP =
  "Job orchestration isn't enabled on this HydroServer instance."

// Mirrors the server's CELERY_ENABLED setting. When it is off, new tasks
// can't be created and existing tasks can't be run, but everything else
// (editing, deleting, data connections, and sub-resources) still works.
export function isOrchestrationEnabled(): boolean {
  return settings.extensionsConfiguration.orchestrationEnabled !== false
}
