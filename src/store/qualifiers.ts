import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export interface Qualifier {
  id: string
  code: string
  description: string
}

export interface QualifierApplication {
  qualifierId: string
  appliedAt: string
  appliedBy: string
}

type ApplicationsByIndex = Record<number, QualifierApplication[]>
type ApplicationsByDatastream = Record<string, ApplicationsByIndex>

const SEED_QUALIFIERS: Qualifier[] = [
  { id: 'q-ice', code: 'ICE', description: 'Ice affected' },
  { id: 'q-mnt', code: 'MNT', description: 'Sensor maintenance' },
  { id: 'q-est', code: 'EST', description: 'Estimated value' },
  { id: 'q-sus', code: 'SUS', description: 'Suspect value' },
  { id: 'q-bad', code: 'BAD', description: 'Bad / unreliable value' },
]

function makeId() {
  return `q-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
}

export const useQualifierStore = defineStore(
  'qualifiers',
  () => {
    const qualifiers = ref<Qualifier[]>([...SEED_QUALIFIERS])
    const applied = ref<ApplicationsByDatastream>({})

    const qualifierById = computed<Record<string, Qualifier>>(() =>
      Object.fromEntries(qualifiers.value.map((q) => [q.id, q]))
    )

    function createQualifier(code: string, description: string): Qualifier {
      const existing = qualifiers.value.find(
        (q) => q.code.toLowerCase() === code.toLowerCase()
      )
      if (existing) return existing

      const q: Qualifier = { id: makeId(), code: code.trim(), description: description.trim() }
      qualifiers.value.push(q)
      return q
    }

    function applyQualifiers(
      datastreamId: string,
      indices: number[],
      qualifierIds: string[],
      appliedBy: string
    ) {
      if (!datastreamId || !indices?.length || !qualifierIds?.length) return

      const appliedAt = new Date().toISOString()
      const dsMap = { ...(applied.value[datastreamId] ?? {}) }

      for (const i of indices) {
        const existing = dsMap[i] ? [...dsMap[i]] : []
        for (const qid of qualifierIds) {
          if (!existing.some((a) => a.qualifierId === qid)) {
            existing.push({ qualifierId: qid, appliedAt, appliedBy })
          }
        }
        dsMap[i] = existing
      }

      applied.value = { ...applied.value, [datastreamId]: dsMap }
    }

    function removeQualifier(
      datastreamId: string,
      index: number,
      qualifierId: string
    ) {
      const dsMap = applied.value[datastreamId]
      if (!dsMap || !dsMap[index]) return
      const remaining = dsMap[index].filter((a) => a.qualifierId !== qualifierId)
      const next = { ...dsMap }
      if (remaining.length) next[index] = remaining
      else delete next[index]
      applied.value = { ...applied.value, [datastreamId]: next }
    }

    /**
     * Returns, for a datastream, one entry per (qualifierId, dataIndex) application
     * suitable for plotting as markers.
     */
    function getApplicationsForDatastream(datastreamId: string) {
      const dsMap = applied.value[datastreamId]
      if (!dsMap) return [] as Array<{
        index: number
        qualifierId: string
        appliedAt: string
        appliedBy: string
      }>
      const out: Array<{
        index: number
        qualifierId: string
        appliedAt: string
        appliedBy: string
      }> = []
      for (const [idxStr, apps] of Object.entries(dsMap)) {
        const index = Number(idxStr)
        for (const a of apps) {
          out.push({ index, ...a })
        }
      }
      return out
    }

    function getApplicationsAtIndex(datastreamId: string, index: number) {
      return applied.value[datastreamId]?.[index] ?? []
    }

    return {
      qualifiers,
      applied,
      qualifierById,
      createQualifier,
      applyQualifiers,
      removeQualifier,
      getApplicationsForDatastream,
      getApplicationsAtIndex,
    }
  },
  { persist: true }
)
