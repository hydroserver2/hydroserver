import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs from '@hydroserver/client'

export const useVocabularyStore = defineStore('vocabulary', () => {
  const userTypes = ref<string[]>([])
  const organizationTypes = ref<string[]>([])
  const siteTypes = ref<string[]>([])
  const samplingFeatureTypes = ref<string[]>([])
  const sensorEncodingTypes = ref<string[]>([])
  const methodTypes = ref<string[]>([])
  const variableTypes = ref<string[]>([])
  const unitTypes = ref<string[]>([])
  const datastreamStatuses = ref<string[]>([])
  const datastreamAggregations = ref<string[]>([])
  const sampledMediums = ref<string[]>([])

  async function fetchUserTypes() {
    const res = await hs.user.getUserTypes()
    userTypes.value = res.data
  }

  async function fetchOrganizationTypes() {
    const res = await hs.user.getOrganizationTypes()
    organizationTypes.value = res.data
  }

  async function fetchSiteTypes() {
    const res = await hs.things.getSiteTypes()
    siteTypes.value = res.data
  }

  async function fetchSamplingFeatureTypes() {
    const res = await hs.things.getSamplingFeatureTypes()
    samplingFeatureTypes.value = res.data
  }

  async function fetchSensorEncodingTypes() {
    const res = await hs.sensors.getEncodingTypes()
    sensorEncodingTypes.value = res.data
  }

  async function fetchMethodTypes() {
    const res = await hs.sensors.getMethodTypes()
    methodTypes.value = res.data
  }

  async function fetchVariableTypes() {
    const res = await hs.observedProperties.getVariableTypes()
    variableTypes.value = res.data
  }

  async function fetchUnitTypes() {
    const res = await hs.units.getTypes()
    unitTypes.value = res.data
  }

  async function fetchDatastreamStatuses() {
    const res = await hs.datastreams.getStatuses()
    datastreamStatuses.value = res.data
  }

  async function fetchDatastreamAggregations() {
    const res = await hs.datastreams.getAggregationStatistics()
    datastreamAggregations.value = res.data
  }

  async function fetchSampledMediums() {
    const res = await hs.datastreams.getSampledMediums()
    sampledMediums.value = res.data
  }

  // Fetch all vocabularies in parallel
  async function fetchAllVocabularies() {
    await Promise.all([
      fetchUserTypes(),
      fetchOrganizationTypes(),
      fetchSiteTypes(),
      fetchSamplingFeatureTypes(),
      fetchSensorEncodingTypes(),
      fetchMethodTypes(),
      fetchVariableTypes(),
      fetchUnitTypes(),
      fetchDatastreamStatuses(),
      fetchDatastreamAggregations(),
      fetchSampledMediums(),
    ])
  }

  return {
    userTypes,
    organizationTypes,
    siteTypes,
    samplingFeatureTypes,
    sensorEncodingTypes,
    methodTypes,
    variableTypes,
    unitTypes,
    datastreamStatuses,
    datastreamAggregations,
    sampledMediums,

    fetchUserTypes,
    fetchOrganizationTypes,
    fetchSiteTypes,
    fetchSamplingFeatureTypes,
    fetchSensorEncodingTypes,
    fetchMethodTypes,
    fetchVariableTypes,
    fetchUnitTypes,
    fetchDatastreamStatuses,
    fetchDatastreamAggregations,
    fetchSampledMediums,

    fetchAllVocabularies,
  }
})
