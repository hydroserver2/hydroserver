/**
 * The one decision point for abandoning the open edit session: taking over
 * with another edit target, and every other exit that ends it.
 *
 * Switching between the Select and Edit views does not end the session, so it
 * never asks. Today leaving is always allowed; the prompts that offer to save,
 * discard or keep the session belong here.
 */

export function useLeaveSession() {
  /** True when the open session may be left behind. */
  async function canLeaveSession(): Promise<boolean> {
    return true
  }

  return { canLeaveSession }
}
