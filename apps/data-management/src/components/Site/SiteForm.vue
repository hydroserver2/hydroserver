<template>
  <v-card>
    <v-card-title class="text-h5"
      >{{ thingId ? 'Edit' : 'Register a' }} Site</v-card-title
    >
    <div class="flex-shrink-0" style="height: 20rem">
      <OpenLayersMap
        v-if="loaded"
        singleMarkerMode
        :startInSatellite="!!thingId"
        @location-clicked="onMapLocationClicked"
        :things="thingId ? [thing] : []"
      />
    </div>
    <v-divider />

    <v-card-text
      class="text-subtitle-2 text-medium-emphasis d-flex align-center"
    >
      <v-icon :icon="mdiInformation" class="mr-1" />
      Click on the map to
      {{ thingId ? 'edit' : 'populate' }}
      site location data.
    </v-card-text>

    <v-form
      ref="myForm"
      v-model="valid"
      validate-on="blur"
      @submit.prevent="uploadThing"
      enctype="multipart/form-data"
    >
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <h6 class="text-h6 my-4">Site Information</h6>
            <v-row>
              <v-col cols="12"
                ><v-text-field
                  label="Site Code *"
                  v-model="thing.samplingFeatureCode"
                  :rules="rules.requiredCode"
              /></v-col>
              <v-col cols="12"
                ><v-text-field
                  label="Site Name *"
                  v-model="thing.name"
                  :rules="rules.requiredAndMaxLength200"
              /></v-col>
              <v-col cols="12"
                ><v-textarea
                  label="Site Description *"
                  v-model="thing.description"
                  :rules="rules.requiredDescription"
              /></v-col>
              <v-col cols="12">
                <v-combobox
                  label="Select Site Type *"
                  :items="vocabularyStore.siteTypes"
                  v-model="thing.siteType"
                  :rules="rules.required"
                />
              </v-col>
            </v-row>
            <v-row no-gutters class="pt-2">
              <v-col>
                <v-switch
                  v-model="includeDataDisclaimer"
                  color="primary"
                  hide-details
                  label="Include a data disclaimer for this site"
                ></v-switch>
              </v-col>
            </v-row>
            <v-row v-if="includeDataDisclaimer" no-gutters>
              <v-col>
                <v-textarea
                  v-model="thing.dataDisclaimer"
                  color="primary"
                ></v-textarea>
              </v-col>
            </v-row>

            <v-row class="mt-2">
              <v-col>
                <RatingCurveTable
                  :thing-id="thingId"
                  :workspace-id="workspaceId"
                  :can-edit="true"
                  :defer-persist="true"
                />
              </v-col>
            </v-row>
          </v-col>
          <v-col cols="12" md="6">
            <h6 class="text-h6 my-4">Site Location</h6>
            <v-row>
              <v-col cols="12" sm="6">
                <v-text-field
                  label="Latitude *"
                  v-model="thing.location.latitude"
                  type="number"
                  :rules="[
                    ...rules.requiredNumber,
                    ...rules.maxLength(22),
                    ...rules.greaterThanOrEqualTo(-90),
                    ...rules.lessThanOrEqualTo(90),
                  ]"
                  validate-on="input"
              /></v-col>
              <v-col cols="12" sm="6"
                ><v-text-field
                  label="Longitude *"
                  v-model="thing.location.longitude"
                  type="number"
                  :rules="[
                    ...rules.requiredNumber,
                    ...rules.maxLength(22),
                    ...rules.greaterThanOrEqualTo(-180),
                    ...rules.lessThanOrEqualTo(180),
                  ]"
                  validate-on="input"
              /></v-col>
              <v-col cols="12" sm="6"
                ><v-text-field
                  label="Elevation (m) *"
                  v-model="thing.location.elevation_m"
                  type="number"
                  :rules="[
                    ...rules.requiredNumber,
                    ...rules.maxLength(22),
                    ...rules.lessThan(1000000),
                    ...rules.greaterThan(-1000000),
                  ]"
                  validate-on="input"
              /></v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  label="State/Province/Region"
                  v-model="thing.location.adminArea1"
                  :rules="thing.location.adminArea1 ? rules.name : []"
                />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  label="County/District"
                  v-model="thing.location.adminArea2"
                  :rules="thing.location.adminArea2 ? rules.name : []"
                />
              </v-col>
              <v-col cols="12" sm="6">
                <v-autocomplete
                  label="Country"
                  :items="countries"
                  :item-title="countryTitle"
                  item-value="code"
                  clearable
                  v-model="thing.location.country"
                >
                  <template v-slot:selection="{ item, index }">
                    <span>{{ thing.location.country }}</span>
                  </template></v-autocomplete
                >
              </v-col>
            </v-row>

            <v-row>
              <v-col>
                <SiteTagManager :thing-id="thingId" />
              </v-col>
            </v-row>

            <v-row>
              <v-col>
                <SitePhotoManager :thing-id="thingId" />
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn-cancel @click="closeDialog">Cancel</v-btn-cancel>
        <v-btn-primary @click="uploadThing">Save</v-btn-primary>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import OpenLayersMap from '@/components/Maps/OpenLayersMap.vue'
import { useThingStore } from '@/store/thing'
import { VForm } from 'vuetify/components'
import { rules } from '@/utils/rules'
import { storeToRefs } from 'pinia'
import SitePhotoManager from '@/components/Site/SitePhotoManager.vue'
import SiteTagManager from '@/components/Site/SiteTagManager.vue'
import RatingCurveTable from '@/components/Orchestration/RatingCurveTable.vue'
import { usePhotosStore } from '@/store/photos'
import { useRatingCurveStore } from '@/store/ratingCurves'
import { useTagStore } from '@/store/tags'
import { Snackbar } from '@/utils/notifications'
import countryList from 'country-list'
import { useVocabularyStore } from '@/composables/useVocabulary'
import hs, { Thing } from '@hydroserver/client'
import { mdiInformation } from '@mdi/js'

const countries = ref<{ name: string; code: string }[]>([])
const countryTitle = (item: { name: string; code: string } | undefined) => {
  if (item && item.code && item.name) return `${item.code} - ${item.name}`
  return ''
}

const { thing: storedThing } = storeToRefs(useThingStore())
const { updatePhotos } = usePhotosStore()
const { updateRatingCurves, resetRatingCurves } = useRatingCurveStore()
const { tags } = storeToRefs(useTagStore())
const { updateTags } = useTagStore()
const vocabularyStore = useVocabularyStore()

const props = defineProps({
  thingId: String,
  workspaceId: { type: String, required: true },
})
const emit = defineEmits(['close', 'site-created'])
let loaded = ref(false)
const valid = ref(false)
const myForm = ref<VForm>()
const thing = reactive<Thing>(new Thing())
const includeDataDisclaimer = ref(thing.dataDisclaimer !== '')

watch(
  () => includeDataDisclaimer.value,
  (newVal) => {
    if (newVal && !thing.dataDisclaimer) {
      thing.dataDisclaimer =
        'WARNING: These data may be provisional and subject to revision. The data are released under the condition that the data collectors may not be held liable for any damages resulting from their use.'
    }
  }
)

async function populateThing() {
  Object.assign(thing, storedThing.value)
  if (thing.location.latitude && thing.location.longitude) loaded.value = true
}

function closeDialog() {
  resetRatingCurves()
  emit('close')
}

async function uploadThing() {
  await myForm.value?.validate()
  if (!valid.value) return
  if (!includeDataDisclaimer.value) thing.dataDisclaimer = ''

  thing.workspaceId = props.workspaceId
  const thingRes = props.thingId
    ? await hs.things.updateItem(thing)
    : await hs.things.createItem(thing)

  if (thingRes) storedThing.value = thingRes

  if (!props.thingId) emit('site-created')

  // Set the tag context to the current site so updateTags can compare
  // against what we already have if anything.
  const tagRes = await hs.things.getTags(storedThing.value!.id)
  tags.value = tagRes.data

  await updateTags(storedThing.value!.id)
  await updatePhotos(storedThing.value!.id)
  const ratingCurveResult = await updateRatingCurves(storedThing.value!.id)
  if (!ratingCurveResult.ok) {
    const firstFailure =
      ratingCurveResult.message ||
      ratingCurveResult.failedCreates[0]?.message ||
      ratingCurveResult.failedMetadataUpdates[0]?.message ||
      ratingCurveResult.failedReplaces[0]?.message ||
      ratingCurveResult.failedDeletes[0]?.message ||
      'Some rating curve changes could not be saved.'
    Snackbar.error(firstFailure)
    return
  }
  closeDialog()
}

function onMapLocationClicked(locationData: Thing) {
  thing.location.latitude = locationData.location.latitude
  thing.location.longitude = locationData.location.longitude
  thing.location.elevation_m = locationData.location.elevation_m
  thing.location.adminArea1 = locationData.location.adminArea1
  thing.location.adminArea2 = locationData.location.adminArea2
  thing.location.country = locationData.location.country
}

onMounted(async () => {
  resetRatingCurves()
  countries.value = countryList.getData()
  if (props.thingId) {
    await populateThing()
    includeDataDisclaimer.value = !!thing.dataDisclaimer
  } else {
    loaded.value = true
  }
})

onUnmounted(() => {
  resetRatingCurves()
})
</script>
