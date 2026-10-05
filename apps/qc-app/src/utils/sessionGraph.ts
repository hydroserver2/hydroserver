/** Sort key for commit order, which is what a later session built on. */
export const commitOrder = (session: {
  committedAt?: string | null
  createdAt: string
}): string => session.committedAt ?? session.createdAt
