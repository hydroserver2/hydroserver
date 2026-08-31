export type HsNavRailItem = {
  id: string
  label: string
  icon: string
  badge?: number
  activeColor?: string
  activeBackground?: string
}

export type HsQueryQualifier = {
  key: string
  label: string
  values: readonly string[]
}
