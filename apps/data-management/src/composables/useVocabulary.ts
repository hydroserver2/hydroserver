import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs from '@hydroserver/client'
import type { SiteTypeIcon } from '@hydroserver/client'

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
    const items = await hs.monitoringSiteTypes.listAllItems()
    siteTypes.value = items.map((item) => item.name)
  }

  async function fetchSiteTypeIcons() {
    const res = await hs.monitoringSites.getSiteTypeIcons()
    if (res.ok) siteTypeIcons.value = res.data
  }

  async function fetchMethodTypes() {
    const items = await hs.methodTypes.listAllItems()
    methodTypes.value = items.map((item) => item.name)
  }

  async function fetchVariableTypes() {
    const items = await hs.observedPropertyTypes.listAllItems()
    variableTypes.value = items.map((item) => item.name)
  }

  async function fetchUnitTypes() {
    const items = await hs.unitTypes.listAllItems()
    unitTypes.value = items.map((item) => item.name)
  }

  async function fetchDatastreamStatuses() {
    const items = await hs.datastreamStatuses.listAllItems()
    datastreamStatuses.value = items.map((item) => item.name)
  }

  async function fetchDatastreamAggregations() {
    const items = await hs.aggregationStatistics.listAllItems()
    datastreamAggregations.value = items.map((item) => item.name)
  }

  async function fetchSampledMediums() {
    const items = await hs.sampledMediums.listAllItems()
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
