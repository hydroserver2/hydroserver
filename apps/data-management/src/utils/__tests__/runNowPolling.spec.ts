import { describe, expect, it } from 'vitest'
import { getRunNowPollDecision } from '../orchestration/runNowPolling'

describe('run-now polling decisions', () => {
  it('waits when no run has been observed yet', () => {
    expect(
      getRunNowPollDecision({
        previousRunId: 'run-0',
      })
    ).toEqual({
      publishQueuedRun: false,
      publishTerminalRun: false,
      hasPublishedQueuedRun: false,
    })
  })

  it('keeps polling silently for the requested run while it is still running', () => {
    expect(
      getRunNowPollDecision({
        requestedRunId: 'run-1',
        observedRunId: 'run-1',
        observedStatus: 'RUNNING',
        hasPublishedQueuedRun: true,
      })
    ).toEqual({
      publishQueuedRun: false,
      publishTerminalRun: false,
      hasPublishedQueuedRun: true,
    })
  })

  it('publishes the final update when the requested run reaches a terminal state', () => {
    expect(
      getRunNowPollDecision({
        requestedRunId: 'run-1',
        observedRunId: 'run-1',
        observedStatus: 'SUCCESS',
        hasPublishedQueuedRun: true,
      })
    ).toEqual({
      publishQueuedRun: false,
      publishTerminalRun: true,
      hasPublishedQueuedRun: true,
    })
  })

  it('ignores the previous latest run while waiting for a newly created run id', () => {
    expect(
      getRunNowPollDecision({
        previousRunId: 'run-0',
        observedRunId: 'run-0',
        observedStatus: 'SUCCESS',
      })
    ).toEqual({
      publishQueuedRun: false,
      publishTerminalRun: false,
      hasPublishedQueuedRun: false,
    })
  })

  it('publishes the queued update once when a new running run is first observed', () => {
    expect(
      getRunNowPollDecision({
        previousRunId: 'run-0',
        observedRunId: 'run-1',
        observedStatus: 'RUNNING',
      })
    ).toEqual({
      publishQueuedRun: true,
      publishTerminalRun: false,
      hasPublishedQueuedRun: true,
    })
  })

  it('waits silently after the queued update has already been published', () => {
    expect(
      getRunNowPollDecision({
        previousRunId: 'run-0',
        observedRunId: 'run-1',
        observedStatus: 'RUNNING',
        hasPublishedQueuedRun: true,
      })
    ).toEqual({
      publishQueuedRun: false,
      publishTerminalRun: false,
      hasPublishedQueuedRun: true,
    })
  })

  it('publishes the final update when the newly observed run is complete', () => {
    expect(
      getRunNowPollDecision({
        previousRunId: 'run-0',
        observedRunId: 'run-1',
        observedStatus: 'FAILURE',
        hasPublishedQueuedRun: true,
      })
    ).toEqual({
      publishQueuedRun: false,
      publishTerminalRun: true,
      hasPublishedQueuedRun: true,
    })
  })
})
