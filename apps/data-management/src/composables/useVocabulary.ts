import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs from '@hydroserver/client'
import type { SiteTypeIcon } from '@hydroserver/client'

export const useVocabularyStore = defineStore('vocabulary', () => {
  const monitoringSiteTypes = ref<string[]>([])
  const siteTypeIcons = ref<SiteTypeIcon[]>([])
  const methodTypes = ref<string[]>([])
  const observedPropertyTypes = ref<string[]>([])
  const unitTypes = ref<string[]>([])
  const datastreamStatuses = ref<string[]>([])
  const aggregationStatistics = ref<string[]>([])
  const sampledMediums = ref<string[]>([])

  async function fetchMonitoringSiteTypes() {
    const items = await hs.monitoringSiteTypes.listAllItems()
    monitoringSiteTypes.value = items.map((item) => item.name)
  }

  async function fetchSiteTypeIcons() {
    const res = await hs.monitoringSites.getSiteTypeIcons()
    if (res.ok) siteTypeIcons.value = res.data
  }

  async function fetchMethodTypes() {
    const items = await hs.methodTypes.listAllItems()
    methodTypes.value = items.map((item) => item.name)
  }

  async function fetchObservedPropertyTypes() {
    const items = await hs.observedPropertyTypes.listAllItems()
    observedPropertyTypes.value = items.map((item) => item.name)
  }

  async function fetchUnitTypes() {
    const items = await hs.unitTypes.listAllItems()
    unitTypes.value = items.map((item) => item.name)
  }

  async function fetchDatastreamStatuses() {
    const items = await hs.datastreamStatuses.listAllItems()
    datastreamStatuses.value = items.map((item) => item.name)
  }

  async function fetchAggregationStatistics() {
    const items = await hs.aggregationStatistics.listAllItems()
    aggregationStatistics.value = items.map((item) => item.name)
  }

  async function fetchSampledMediums() {
    const items = await hs.sampledMediums.listAllItems()
    sampledMediums.value = items.map((item) => item.name)
  }

  // Fetch all vocabularies in parallel
  async function fetchAllVocabularies() {
    await Promise.all([
      fetchMonitoringSiteTypes(),
      fetchSiteTypeIcons(),
      fetchMethodTypes(),
      fetchObservedPropertyTypes(),
      fetchUnitTypes(),
      fetchDatastreamStatuses(),
      fetchAggregationStatistics(),
      fetchSampledMediums(),
    ])
  }

  return {
    monitoringSiteTypes,
    siteTypeIcons,
    methodTypes,
    observedPropertyTypes,
    unitTypes,
    datastreamStatuses,
    aggregationStatistics,
    sampledMediums,

    fetchMonitoringSiteTypes,
    fetchSiteTypeIcons,
    fetchMethodTypes,
    fetchObservedPropertyTypes,
    fetchUnitTypes,
    fetchDatastreamStatuses,
    fetchAggregationStatistics,
    fetchSampledMediums,

    fetchAllVocabularies,
  }
})
