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
    const res = await hs.monitoringSites.getSiteTypes()
    if (res.ok) siteTypes.value = res.data
  }

  async function fetchSiteTypeIcons() {
    const res = await hs.monitoringSites.getSiteTypeIcons()
    if (res.ok) siteTypeIcons.value = res.data
  }

  async function fetchMethodTypes() {
    const res = await hs.methods.getTypes()
    if (res.ok) methodTypes.value = res.data
  }

  async function fetchVariableTypes() {
    const res = await hs.observedProperties.getVariableTypes()
    if (res.ok) variableTypes.value = res.data
  }

  async function fetchUnitTypes() {
    const res = await hs.units.getTypes()
    if (res.ok) unitTypes.value = res.data
  }

  async function fetchDatastreamStatuses() {
    const res = await hs.datastreams.getStatuses()
    if (res.ok) datastreamStatuses.value = res.data
  }

  async function fetchDatastreamAggregations() {
    const res = await hs.datastreams.getAggregationStatistics()
    if (res.ok) datastreamAggregations.value = res.data
  }

  async function fetchSampledMediums() {
    const res = await hs.datastreams.getSampledMediums()
    if (res.ok) sampledMediums.value = res.data
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
