type NullableRunStatus = string | null | undefined

export type RunNowPollDecision = {
  publishQueuedRun: boolean
  publishTerminalRun: boolean
  hasPublishedQueuedRun: boolean
}

type GetRunNowPollDecisionParams = {
  requestedRunId?: string | null
  previousRunId?: string | null
  observedRunId?: string | null
  observedStatus?: NullableRunStatus
  hasPublishedQueuedRun?: boolean
}

const EMPTY_DECISION: RunNowPollDecision = {
  publishQueuedRun: false,
  publishTerminalRun: false,
  hasPublishedQueuedRun: false,
}

const isTerminalRunStatus = (status?: NullableRunStatus) =>
  typeof status === 'string' && status !== 'RUNNING'

export const getRunNowPollDecision = ({
  requestedRunId = null,
  previousRunId = null,
  observedRunId = null,
  observedStatus,
  hasPublishedQueuedRun = false,
}: GetRunNowPollDecisionParams): RunNowPollDecision => {
  if (!observedRunId) {
    return {
      ...EMPTY_DECISION,
      hasPublishedQueuedRun,
    }
  }

  const observedRequestedRun = requestedRunId
    ? observedRunId === requestedRunId
    : previousRunId
      ? observedRunId !== previousRunId
      : true

  if (!observedRequestedRun) {
    return {
      ...EMPTY_DECISION,
      hasPublishedQueuedRun,
    }
  }

  const terminal = isTerminalRunStatus(observedStatus)

  if (requestedRunId) {
    return {
      publishQueuedRun: false,
      publishTerminalRun: terminal,
      hasPublishedQueuedRun: true,
    }
  }

  if (!hasPublishedQueuedRun && !terminal) {
    return {
      publishQueuedRun: true,
      publishTerminalRun: false,
      hasPublishedQueuedRun: true,
    }
  }

  if (terminal) {
    return {
      publishQueuedRun: false,
      publishTerminalRun: true,
      hasPublishedQueuedRun: true,
    }
  }

  return {
    ...EMPTY_DECISION,
    hasPublishedQueuedRun,
  }
}
