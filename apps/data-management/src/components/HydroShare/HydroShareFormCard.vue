<template>
  <HydroShareDeleteCard
    v-if="thing?.id && openDelete"
    :thing-id="thing.id"
    @close="openDelete = false"
    @delete="onDelete"
  />
  <v-card v-else-if="!openDelete">
    <v-card-title>
      <v-row class="text-h5">
        <v-col v-if="linkToExistingAccount">
          Link Site to HydroShare Archival Resource
        </v-col>
        <v-col v-else>
          {{ isEdit ? 'Update' : 'Create' }} HydroShare Archival Resource
        </v-col>
        <v-spacer />
        <v-col cols="auto" v-if="isEdit">
          <v-btn @click="archiveThing">
            <v-icon :icon="mdiUpload" left />
            Archive Now
          </v-btn>
        </v-col>
      </v-row>
    </v-card-title>

    <v-divider />

    <v-form
      @submit.prevent="onSubmit"
      ref="myForm"
      v-model="valid"
      validate-on="blur"
      :disabled="loading"
    >
      <h6 v-if="false" class="text-h6 my-4 d-flex justify-center align-center">
        Archival Scheduling

        <v-tooltip open-delay="500">
          <template v-slot:activator="{ props }">
            <v-icon
              size="small"
              class="ml-2"
              color="grey lighten-1"
              v-bind="props"
              :icon="mdiHelpCircleOutline"
            />
          </template>
          <template v-slot:default>
            <p>
              Site data are archived to HydroShare at midnight MST (at the
              beginning of the week/month for weekly/monthly scheduled sites)
            </p>
          </template>
        </v-tooltip>
      </h6>

      <v-card-text v-if="false" class="my-3 d-flex justify-center">
        <v-btn
          v-for="selection in scheduleSelections"
          rounded
          :variant="item.frequency === selection.value ? 'outlined' : 'plain'"
          @click="item.frequency = selection.value"
          >{{ selection.text }}</v-btn
        >
      </v-card-text>

      <v-card-text>
        <div v-if="isEdit">
          <v-row class="mb-2">
            <v-col>
              <v-btn
                class="px-0"
                variant="text"
                :href="item.link"
                target="_blank"
              >
                Edit this resource in HydroShare
              </v-btn>
            </v-col>
            <v-spacer />
            <v-col cols="auto" color="red">
              <v-btn
                class="px-0"
                color="delete"
                variant="text"
                @click="openDelete = true"
              >
                Unlink this site from HydroShare
              </v-btn>
            </v-col>
          </v-row>
        </div>

        <div v-if="!isEdit">
          <v-radio-group v-model="linkToExistingAccount" inline>
            <v-radio label="Create New Resource" :value="false" />
            <v-radio label="Link Site to Existing Resource" :value="true" />
          </v-radio-group>

          <div v-if="!linkToExistingAccount">
            <v-text-field
              label="Resource Title *"
              v-model="item.resourceTitle"
              :rules="rules.required"
            />
            <v-textarea
              label="Resource Abstract *"
              v-model="item.resourceAbstract"
              :rules="rules.required"
            />
            <v-combobox
              label="Resource Keywords *"
              v-model="item.resourceKeywords"
              multiple
              :rules="rules.minLength(1)"
            >
              <template v-slot:selection="{ item, index }">
                <v-chip
                  color="blue-grey"
                  rounded
                  closable
                  @click:close="removeKeyword(index)"
                >
                  <span>{{ item.title }}</span>
                </v-chip>
              </template>
            </v-combobox>
          </div>
        </div>

        <v-text-field
          v-if="linkToExistingAccount || isEdit"
          v-model="item.link"
          label="HydroShare Resource Link (URL) *"
          placeholder="https://www.hydroshare.org/resource/9429f876dc71958d93f22909f2cb12f3/"
          :rules="hydroShareUrl"
          class="mb-4"
        />

        <v-text-field
          label="Resource Folder Name *"
          v-model="item.path"
          :rules="rules.required"
          class="mb-4"
        />

        <v-autocomplete
          label="Included Datastreams *"
          v-model="item.datastreamIds"
          :items="datastreams"
          :item-title="datastreamTitle"
          item-value="id"
          multiple
          :rules="rules.minLength(1)"
        >
          <template v-slot:selection="{ item, index }">
            <v-chip
              color="blue-grey"
              rounded
              closable
              @click:close="removeDatastream(index)"
            >
              <span>{{ item.title }}</span>
            </v-chip>
          </template>
        </v-autocomplete>

        <v-checkbox
          v-if="!isEdit && !linkToExistingAccount"
          v-model="item.publicResource"
          label="Make resource public"
          color="primary"
          hide-details
        />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="emit('close')">Close</v-btn-cancel>
        <v-btn-primary @click="onSubmit">{{
          isEdit ? 'Update' : 'Create'
        }}</v-btn-primary>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { useThingStore } from '@/store/thing'
import { storeToRefs } from 'pinia'
import { onMounted, ref } from 'vue'
import hs, {
  Datastream,
  PostHydroShareArchive,
  Frequency,
} from '@hydroserver/client'
import { VForm } from 'vuetify/components'
import { hydroShareUrl, rules } from '@/utils/rules'
import { useFormLogic } from '@/composables/useFormLogic'
import HydroShareDeleteCard from '@/components/HydroShare/HydroShareDeleteCard.vue'
import { useHydroShareStore } from '@/store/hydroShare'
import { Snackbar } from '@/utils/notifications'
import { mdiHelpCircleOutline, mdiUpload } from '@mdi/js'

const emit = defineEmits(['close', 'delete'])
const { hydroShareArchive: archive, loading } = storeToRefs(
  useHydroShareStore()
)

const { item, isEdit, valid, myForm, uploadItem } = useFormLogic(
  hs.things.createHydroShareArchive,
  hs.things.updateHydroShareArchive,
  PostHydroShareArchive,
  archive.value || undefined
)

const { thing } = storeToRefs(useThingStore())
const datastreams = ref<Datastream[]>([])
const linkToExistingAccount = ref(false)
const openDelete = ref(false)

type ScheduleSelection = {
  value: Frequency
  text: string
}

const scheduleSelections: ScheduleSelection[] = [
  { value: 'daily', text: 'Daily' },
  { value: 'weekly', text: 'Weekly' },
  { value: 'monthly', text: 'Monthly' },
  { value: null, text: "Don't schedule" },
]

function removeKeyword(index: number) {
  if (item.value.resourceKeywords) item.value.resourceKeywords.splice(index, 1)
}

const datastreamTitle = (item: Datastream) => `${item.description} - ${item.id}`

function removeDatastream(index: number) {
  item.value.datastreamIds.splice(index, 1)
}

const generateKeywords = () => {
  const mediumsSet = new Set(datastreams.value.map((ds) => ds.sampledMedium))
  const EXCLUDED_MEDIUMS = ['Not applicable', 'Unknown', 'Other']
  EXCLUDED_MEDIUMS.forEach((medium) => mediumsSet.delete(medium))
  if (thing.value?.siteType) mediumsSet.add(thing.value.siteType)
  return ['HydroServer Site Archive', ...mediumsSet]
}

function generateDefaultFormData() {
  item.value.thingId = thing.value!.id
  item.value.path = 'HydroServer'
  item.value.resourceKeywords = generateKeywords()
  item.value.resourceTitle = `HydroServer Archive: ${thing.value?.name}`
  item.value.publicResource = !thing.value?.isPrivate
  item.value.datastreamIds = datastreams.value.map((ds) => ds.id)
  item.value.resourceAbstract =
    `This HydroShare resource serves as an archive for monitoring data collected at ` +
    `${thing.value?.name}. The datasets contained herein represent a collection of hydrologic observations ` +
    `collected at this location. The purpose of this archive is to provide a centralized repository for the ` +
    `hydrologic data recorded at this site, facilitating accessibility, analysis, and collaboration among ` +
    `researchers and stakeholders.`
}

async function onDelete() {
  archive.value = null
  emit('close')
}

async function onSubmit() {
  try {
    loading.value = true
    if (!linkToExistingAccount.value) item.value.link = ''
    emit('close')
    Snackbar.info('Uploading site data to HydroShare. This may take a minute.')
    const newItem = await uploadItem()
    if (!newItem) return
    archive.value = newItem
  } catch (error) {
    Snackbar.error('Failed to upload site data to HydroShare')
    console.error('Error archiving to HydroShare', error)
  } finally {
    loading.value = false
  }
}

const archiveThing = async () => {
  try {
    loading.value = true
    emit('close')
    Snackbar.info('Uploading site data to HydroShare. This may take a minute.')
    await hs.things.triggerHydroShareArchive(thing.value!.id)
  } catch (error) {
    Snackbar.error('Failed to upload site data to HydroShare')
    console.error('Error archiving to HydroShare', error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  datastreams.value = await hs.datastreams.listAllItems({
    thing_id: [thing.value!.id],
  })
  if (!isEdit.value) generateDefaultFormData()
})
</script>
