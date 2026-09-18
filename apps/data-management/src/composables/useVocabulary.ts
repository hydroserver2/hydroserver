import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs from '@hydroserver/client'
import type { SiteTypeIcon } from '@hydroserver/client'

const GLOBAL_ACTIVE_TERMS = {
  workspace_id: ['null'] as 'null'[],
  is_active: true,
}

export const useVocabularyStore = defineStore('vocabulary', () => {
  const siteTypes = ref<string[]>([])
  const siteTypeIcons = ref<SiteTypeIcon[]>([])
  const methodTypes = ref<string[]>([])
  const variableTypes = ref<string[]>([])
  const unitTypes = ref<string[]>([])
  const datastreamStatuses = ref<string[]>([])
  const datastreamAggregations = ref<string[]>([])
  const sampledMediums = ref<string[]>([])

  async function fetchSiteTypes() {
    const items = await hs.monitoringSiteTypes.listAllItems(GLOBAL_ACTIVE_TERMS)
    siteTypes.value = items.map((item) => item.name)
  }

  async function fetchSiteTypeIcons() {
    const res = await hs.monitoringSites.getSiteTypeIcons()
    if (res.ok) siteTypeIcons.value = res.data
  }

  async function fetchMethodTypes() {
    const items = await hs.methodTypes.listAllItems(GLOBAL_ACTIVE_TERMS)
    methodTypes.value = items.map((item) => item.name)
  }

  async function fetchVariableTypes() {
    const items = await hs.observedPropertyTypes.listAllItems(GLOBAL_ACTIVE_TERMS)
    variableTypes.value = items.map((item) => item.name)
  }

  async function fetchUnitTypes() {
    const items = await hs.unitTypes.listAllItems(GLOBAL_ACTIVE_TERMS)
    unitTypes.value = items.map((item) => item.name)
  }

  async function fetchDatastreamStatuses() {
    const items = await hs.datastreamStatuses.listAllItems(GLOBAL_ACTIVE_TERMS)
    datastreamStatuses.value = items.map((item) => item.name)
  }

  async function fetchDatastreamAggregations() {
    const items = await hs.aggregationStatistics.listAllItems(GLOBAL_ACTIVE_TERMS)
    datastreamAggregations.value = items.map((item) => item.name)
  }

  async function fetchSampledMediums() {
    const items = await hs.sampledMediums.listAllItems(GLOBAL_ACTIVE_TERMS)
    sampledMediums.value = items.map((item) => item.name)
  }

  // Fetch all vocabularies in parallel
  async function fetchAllVocabularies() {
    await Promise.all([
      fetchSiteTypes(),
      fetchSiteTypeIcons(),
      fetchMethodTypes(),
      fetchVariableTypes(),
      fetchUnitTypes(),
      fetchDatastreamStatuses(),
      fetchDatastreamAggregations(),
      fetchSampledMediums(),
    ])
  }

  return {
    siteTypes,
    siteTypeIcons,
    methodTypes,
    variableTypes,
    unitTypes,
    datastreamStatuses,
    datastreamAggregations,
    sampledMediums,

    fetchSiteTypes,
    fetchSiteTypeIcons,
    fetchMethodTypes,
    fetchVariableTypes,
    fetchUnitTypes,
    fetchDatastreamStatuses,
    fetchDatastreamAggregations,
    fetchSampledMediums,

    fetchAllVocabularies,
  }
})
