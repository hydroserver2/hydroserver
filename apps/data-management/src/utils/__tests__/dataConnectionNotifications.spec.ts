import { describe, expect, it } from 'vitest'
import { DataConnection } from '@hydroserver/client'
import {
  DEFAULT_NOTIFICATION_CRONTAB,
  ensureNotificationSchedule,
} from '@/utils/orchestration/dataConnectionNotifications'

describe('ensureNotificationSchedule', () => {
  it('adds a daily 9am schedule when notification recipients are present', () => {
    const dataConnection = new DataConnection({
      notification: {
        recipientEmails: ['user@example.com'],
      },
    })

    ensureNotificationSchedule(dataConnection)

    expect(dataConnection.notification?.schedule).toEqual({
      enabled: true,
      crontab: DEFAULT_NOTIFICATION_CRONTAB,
      interval: null,
      intervalPeriod: null,
      startTime: null,
    })
  })

  it('keeps an existing notification schedule intact', () => {
    const schedule = {
      enabled: false,
      crontab: '30 8 * * *',
      interval: null,
      intervalPeriod: null,
      startTime: null,
    }
    const dataConnection = new DataConnection({
      notification: {
        recipientEmails: ['user@example.com'],
        schedule,
      },
    })

    ensureNotificationSchedule(dataConnection)

    expect(dataConnection.notification?.schedule).toBe(schedule)
  })

  it('does not add a schedule when no notification recipients are present', () => {
    const dataConnection = new DataConnection({
      notification: {
        recipientEmails: [],
      },
    })

    ensureNotificationSchedule(dataConnection)

    expect(dataConnection.notification?.schedule).toBeUndefined()
  })
})
