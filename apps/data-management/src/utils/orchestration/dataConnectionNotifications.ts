import type { DataConnection, NotificationSchedule } from '@hydroserver/client'

export const DEFAULT_NOTIFICATION_CRONTAB = '0 9 * * *'

const createDefaultNotificationSchedule = (): NotificationSchedule => ({
  enabled: true,
  crontab: DEFAULT_NOTIFICATION_CRONTAB,
  interval: null,
  intervalPeriod: null,
  startTime: null,
})

export const ensureNotificationSchedule = (
  dataConnection: DataConnection
): DataConnection => {
  const notification = dataConnection.notification
  const recipientEmails = notification?.recipientEmails ?? []

  if (recipientEmails.length > 0 && !notification?.schedule) {
    notification!.schedule = createDefaultNotificationSchedule()
  }

  return dataConnection
}
