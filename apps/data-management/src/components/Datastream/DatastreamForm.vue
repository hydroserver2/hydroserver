<template>
  <v-card>
    <v-toolbar color="white">
      <v-card-title> {{ isEdit ? 'Edit' : 'Create' }} datastream </v-card-title>
      <v-spacer />
      <v-btn
        v-if="!isEdit"
        color="primary-darken-2"
        class="mr-4"
        variant="outlined"
        rounded="lg"
        @click="showTemplateModal = true"
        :prepend-icon="mdiImport"
        >Load template</v-btn
      >
    </v-toolbar>

    <v-dialog v-model="showTemplateModal" width="75rem">
      <DatastreamSelectorCard
        card-title="Use an existing datastream as a template"
        @selected-datastream="selectedDatastreamID = $event.id"
        @close="showTemplateModal = false"
      />
    </v-dialog>

    <v-divider />

    <v-form
      v-if="datastream"
      @submit.prevent="onSubmit"
      ref="myForm"
      v-model="valid"
      validate-on="input"
    >
      <v-row>
        <v-col cols="12" md="6">
          <v-card-title
            >Linked metadata
            <v-icon
              :icon="mdiHelpCircleOutline"
              size="x-small"
              class="ml-2"
              @click="showLinkedMetadataHelp = !showLinkedMetadataHelp"
            />
          </v-card-title>
          <v-card-text
            v-if="showLinkedMetadataHelp"
            class="text-subtitle-2 text-medium-emphasis"
          >
            Select the appropriate metadata to describe the the datastream you
            are adding to the monitoring site. If you want to modify the values
            available in the drop down menus below, click the "+" button or
            visit the
            <router-link to="/Metadata"> Manage metadata page. </router-link>
            Options in the drop down menus come from both metadata associated
            with the workspace as well as system level metadata managed by the
            system admin.
          </v-card-text>

          <v-card-text>
            <v-autocomplete
              :key="datastream.sensorId"
              v-model="datastream.sensorId"
              label="Select sensor *"
              :items="sensors"
              item-title="name"
              item-value="id"
              :rules="rules.required"
              no-data-text="No available sensors"
              :prepend-inner-icon="mdiSignalVariant"
              density="compact"
              rounded="lg"
            >
              <template v-slot:item="{ props, item }">
                <v-tooltip
                  bottom
                  :openDelay="500"
                  content-class="pa-0 ma-0 bg-transparent"
                >
                  <template #activator="{ props: tooltipProps }">
                    <v-list-item
                      v-bind="{ ...props, ...tooltipProps }"
                      :subtitle="
                        item.raw.workspaceId == null
                          ? 'System variable'
                          : 'Workspace variable'
                      "
                      :class="
                        item.raw.workspaceId == null ? 'bg-grey-lighten-5' : ''
                      "
                    />
                  </template>

                  <InfoCard
                    :title="item.raw.name"
                    :subtitle="{
                      label: 'Method type',
                      value: item.raw.methodType,
                    }"
                    :items="[
                      { label: 'Description', value: item.raw.description },
                      { label: 'Make', value: item.raw.manufacturer },
                      { label: 'Model', value: item.raw.model },
                      { label: 'Method Code', value: item.raw.methodCode },
                      { label: 'Method Link', value: item.raw.methodLink },
                      { label: 'Encoding Type', value: item.raw.encodingType },
                      { label: 'Model Link', value: item.raw.modelLink },
                    ]"
                    :isWorkspace="!!item.raw.workspaceId"
                  />
                </v-tooltip>
              </template>

              <template
                v-slot:append
                v-if="
                  hasPermission(
                    PermissionResource.Sensor,
                    PermissionAction.Create,
                    workspace
                  )
                "
              >
                <v-icon
                  :icon="mdiPlus"
                  color="secondary-darken-2"
                  @click="showSensorModal = true"
                />
                <v-dialog v-model="showSensorModal" width="30rem">
                  <SensorFormCard
                    v-if="workspace"
                    :workspace-id="workspace.id"
                    @created="handleMetadataUploaded('sensorId', $event)"
                    @close="showSensorModal = false"
                  />
                </v-dialog>
              </template>
            </v-autocomplete>

            <v-autocomplete
              v-model="datastream.observedPropertyId"
              label="Select observed property *"
              :items="formattedObservedProperties"
              item-title="title"
              item-value="id"
              :rules="rules.required"
              no-data-text="No available properties"
              :prepend-inner-icon="mdiWaterThermometer"
              density="compact"
              rounded="lg"
              class="mt-2"
            >
              <template v-slot:item="{ props, item }">
                <v-tooltip
                  bottom
                  :openDelay="500"
                  content-class="pa-0 ma-0 bg-transparent"
                >
                  <template v-slot:activator="{ props: tooltipProps }">
                    <v-list-item
                      :subtitle="
                        item.raw.workspaceId === null
                          ? 'System variable'
                          : 'Workspace variable'
                      "
                      :class="
                        item.raw.workspaceId === null ? 'bg-grey-lighten-5' : ''
                      "
                      v-bind="{ ...props, ...tooltipProps }"
                    >
                    </v-list-item>
                  </template>
                  <InfoCard
                    :title="item.raw.name"
                    :subtitle="{ label: 'Code', value: item.raw.code }"
                    :items="[
                      {
                        label: 'Definition',
                        value: item.raw.definition,
                      },
                      {
                        label: 'Description',
                        value: item.raw.description,
                      },
                      { label: 'Type', value: item.raw.type },
                    ]"
                    :isWorkspace="!!item.raw.workspaceId"
                  />
                </v-tooltip>
              </template>
              <template
                v-slot:append
                v-if="
                  hasPermission(
                    PermissionResource.ObservedProperty,
                    PermissionAction.Create,
                    workspace
                  )
                "
              >
                <v-icon
                  :icon="mdiPlus"
                  color="secondary-darken-2"
                  @click="showOPModal = true"
                />
                <v-dialog v-model="showOPModal" width="30rem">
                  <ObservedPropertyFormCard
                    v-if="workspace"
                    :workspace-id="workspace.id"
                    @created="
                      handleMetadataUploaded('observedPropertyId', $event)
                    "
                    @close="showOPModal = false"
                  />
                </v-dialog>
              </template>
            </v-autocomplete>

            <v-autocomplete
              v-model="datastream.unitId"
              label="Select unit *"
              :items="units"
              item-title="name"
              item-value="id"
              :rules="rules.required"
              no-data-text="No available units"
              :prepend-inner-icon="mdiTapeMeasure"
              density="compact"
              rounded="lg"
              class="mt-2"
            >
              <template #item="{ props, item }">
                <v-tooltip
                  bottom
                  :openDelay="500"
                  content-class="pa-0 ma-0 bg-transparent"
                >
                  <template #activator="{ props: tooltipProps }">
                    <v-list-item
                      v-bind="{ ...props, ...tooltipProps }"
                      :subtitle="
                        item.raw.workspaceId == null
                          ? 'System unit'
                          : 'Workspace unit'
                      "
                      :class="
                        item.raw.workspaceId == null ? 'bg-grey-lighten-5' : ''
                      "
                    />
                  </template>

                  <InfoCard
                    :title="item.raw.name"
                    :subtitle="{ label: 'Symbol', value: item.raw.symbol }"
                    :items="[
                      { label: 'Definition', value: item.raw.definition },
                      { label: 'Type', value: item.raw.type },
                    ]"
                    :isWorkspace="!!item.raw.workspaceId"
                  />
                </v-tooltip>
              </template>

              <template
                #append
                v-if="
                  hasPermission(
                    PermissionResource.Unit,
                    PermissionAction.Create,
                    workspace
                  )
                "
              >
                <v-icon
                  :icon="mdiPlus"
                  color="secondary-darken-2"
                  @click="openUnitForm = true"
                />
                <v-dialog v-model="openUnitForm" width="30rem">
                  <UnitFormCard
                    v-if="workspace"
                    :workspace-id="workspace.id"
                    @created="handleMetadataUploaded('unitId', $event)"
                    @close="openUnitForm = false"
                  />
                </v-dialog>
              </template>
            </v-autocomplete>

            <v-autocomplete
              v-model="datastream.processingLevelId"
              label="Select processing level *"
              :items="formattedProcessingLevels"
              item-title="title"
              item-value="id"
              :rules="rules.required"
              no-data-text="No available processing level"
              :prepend-inner-icon="mdiCheckCircle"
              density="compact"
              rounded="lg"
              class="mt-2"
            >
              <template #item="{ props, item }">
                <v-tooltip
                  bottom
                  :openDelay="500"
                  content-class="pa-0 ma-0 bg-transparent"
                >
                  <template #activator="{ props: tooltipProps }">
                    <v-list-item
                      v-bind="{ ...props, ...tooltipProps }"
                      :subtitle="
                        item.raw.workspaceId == null
                          ? 'System level'
                          : 'Workspace level'
                      "
                      :class="
                        item.raw.workspaceId == null ? 'bg-grey-lighten-5' : ''
                      "
                    />
                  </template>

                  <InfoCard
                    :title="item.raw.definition"
                    :subtitle="{
                      label: 'Code',
                      value: item.raw.code,
                    }"
                    :items="[
                      { label: 'Explanation', value: item.raw.explanation },
                    ]"
                    :isWorkspace="!!item.raw.workspaceId"
                  />
                </v-tooltip>
              </template>

              <template
                #append
                v-if="
                  hasPermission(
                    PermissionResource.ProcessingLevel,
                    PermissionAction.Create,
                    workspace
                  )
                "
              >
                <v-icon
                  :icon="mdiPlus"
                  color="secondary-darken-2"
                  @click="showPLModal = true"
                />
                <v-dialog v-model="showPLModal" width="30rem">
                  <ProcessingLevelFormCard
                    v-if="workspace"
                    :workspace-id="workspace.id"
                    @created="
                      handleMetadataUploaded('processingLevelId', $event)
                    "
                    @close="showPLModal = false"
                  />
                </v-dialog>
              </template>
            </v-autocomplete>
          </v-card-text>
        </v-col>

        <v-col cols="12" md="6">
          <v-card-title>Time spacing</v-card-title>
          <v-card-text>
            <v-text-field
              v-model="datastream.timeAggregationInterval"
              label="Time aggregation interval *"
              :rules="[
                ...rules.requiredNumber,
                () =>
                  datastream.timeAggregationIntervalUnit != null ||
                  'An interval must be selected.',
              ]"
              type="number"
              density="compact"
              rounded="lg"
              :prepend-inner-icon="mdiClockTimeThree"
            />

            <v-col
              cols="12"
              align="center"
              justify="center"
              class="no-wrap pt-0 mb-4"
            >
              <v-btn-toggle
                v-model="datastream.timeAggregationIntervalUnit"
                label="Time aggregation unit *"
                :items="timeUnits"
                variant="outlined"
                color="primary"
                density="compact"
                rounded="xl"
                divided
                mandatory
              >
                <v-btn v-for="unit in timeUnits" :value="unit">{{
                  unit
                }}</v-btn>
              </v-btn-toggle>
            </v-col>

            <v-text-field
              ref="intendedTimeSpacingRef"
              v-model="datastream.intendedTimeSpacing"
              label="Intended time spacing"
              :rules="[
                () =>
                  !datastream.intendedTimeSpacing ||
                  datastream.intendedTimeSpacingUnit != null ||
                  'Unit is required when a time spacing value is provided.',
              ]"
              type="number"
              density="compact"
              rounded="lg"
              :prepend-inner-icon="mdiTimer"
            />

            <v-col
              cols="12"
              align="center"
              justify="center"
              class="no-wrap pt-0"
            >
              <v-btn-toggle
                v-model="datastream.intendedTimeSpacingUnit"
                label="Intended time spacing unit"
                :items="timeUnits"
                variant="outlined"
                color="primary"
                density="compact"
                rounded="xl"
                @update:model-value="onSpacingUnitChange"
                divided
              >
                <v-btn v-for="unit in timeUnits" :value="unit">{{
                  unit
                }}</v-btn>
              </v-btn-toggle>
            </v-col>
          </v-card-text>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="6">
          <v-card-title>Datastream attributes</v-card-title>
          <v-card-text class="text-subtitle-2 text-medium-emphasis">
            For the following items, select an option or type your own. Note:
            the default selections won't be available if there is custom text in
            the field.
          </v-card-text>
          <v-card-text class="pb-0">
            <v-combobox
              :items="vocabularyStore.sampledMediums"
              v-model="datastream.sampledMedium"
              label="Medium *"
              :rules="rules.required"
              density="compact"
              rounded="xl"
              :prepend-inner-icon="mdiAirFilter"
            />

            <v-combobox
              :items="vocabularyStore.datastreamStatuses"
              v-model="datastream.status"
              label="Status"
              density="compact"
              rounded="xl"
              :prepend-inner-icon="mdiListStatus"
            />

            <v-combobox
              :items="vocabularyStore.datastreamAggregations"
              v-model="datastream.aggregationStatistic"
              label="Aggregation statistic *"
              :rules="rules.requiredAndMaxLength255"
              density="compact"
              rounded="xl"
              :prepend-inner-icon="mdiTableColumn"
            />
          </v-card-text>

          <v-card-text class="text-subtitle-2 text-medium-emphasis pt-2">
            When observation data is missing a value, what should the default
            be?
          </v-card-text>
          <v-card-text>
            <v-text-field
              v-model="datastream.noDataValue"
              label="No data value *"
              :rules="rules.required"
              type="number"
              density="compact"
              rounded="lg"
              :prepend-inner-icon="mdiCircleOffOutline"
            />
          </v-card-text>
        </v-col>

        <v-col cols="12" md="6">
          <v-card-title>Name and description</v-card-title>
          <v-card-text class="text-subtitle-2 text-medium-emphasis">
            Enter a name and description for this datastream, or opt to
            auto-fill with default text. If you choose the defaults, make sure
            you've first filled out the rest of the form correctly as the
            website will generate text based on the current form fields.
          </v-card-text>

          <v-card-text>
            <v-text-field
              v-model="datastream.name"
              label="Datastream name *"
              :rules="rules.requiredAndMaxLength255"
              density="compact"
              rounded="lg"
            />

            <v-row justify="end">
              <v-col cols="auto">
                <v-spacer />
                <v-btn
                  variant="text"
                  color="grey-darken-4"
                  :disabled="datastream.name === originalName"
                  @click="datastream.name = originalName"
                >
                  Revert
                </v-btn>
                <v-btn
                  color="primary-darken-2"
                  variant="outlined"
                  rounded="xl"
                  class="ml-2"
                  @click="datastream.name = generateDefaultName()"
                  >Auto-Fill from Form</v-btn
                >
              </v-col>
            </v-row>
          </v-card-text>

          <v-card-text>
            <v-textarea
              v-model="datastream.description"
              label="Datastream description *"
              :rules="rules.requiredDescription"
              rounded="lg"
            />

            <v-row justify="end">
              <v-col cols="auto">
                <v-spacer />
                <v-btn
                  variant="text"
                  color="grey-darken-4"
                  :disabled="datastream.description === originalDescription"
                  @click="datastream.description = originalDescription"
                >
                  Revert
                </v-btn>
                <v-btn
                  color="primary-darken-2"
                  variant="outlined"
                  rounded="xl"
                  class="ml-2"
                  @click="datastream.description = generateDefaultDescription()"
                  >Auto-Fill from Form</v-btn
                >
              </v-col>
            </v-row>
          </v-card-text>
        </v-col>
      </v-row>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="emit('close')"> Cancel </v-btn-cancel>
        <v-btn-primary type="submit" class="my-4"
          >{{ isEdit ? 'Update' : 'Create' }} datastream</v-btn-primary
        >
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, toRef } from 'vue'
import DatastreamSelectorCard from '@/components/Datastream/DatastreamSelectorCard.vue'
import SensorFormCard from '@/components/Metadata/SensorFormCard.vue'
import ObservedPropertyFormCard from '@/components/Metadata/ObservedPropertyFormCard.vue'
import UnitFormCard from '@/components/Metadata/UnitFormCard.vue'
import ProcessingLevelFormCard from '@/components/Metadata/ProcessingLevelFormCard.vue'
import { rules } from '@/utils/rules'
import { Snackbar } from '@/utils/notifications'
import { useMetadata } from '@/composables/useMetadata'
import { VForm } from 'vuetify/components'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useVocabularyStore } from '@/composables/useVocabulary'
import InfoCard from '../Metadata/InfoCard.vue'
import hs, {
  PermissionAction,
  PermissionResource,
  Thing,
  Datastream,
  Workspace,
} from '@hydroserver/client'
import {
  mdiAirFilter,
  mdiCheckCircle,
  mdiCircleOffOutline,
  mdiClockTimeThree,
  mdiHelpCircleOutline,
  mdiImport,
  mdiListStatus,
  mdiPlus,
  mdiSignalVariant,
  mdiTableColumn,
  mdiTapeMeasure,
  mdiTimer,
  mdiWaterThermometer,
} from '@mdi/js'

const emit = defineEmits(['close', 'updated', 'created'])

const props = defineProps({
  thing: { type: Object as () => Thing, required: true },
  workspace: { type: Object as () => Workspace, required: true },
  datastream: { type: Object as () => Datastream, required: false },
})

const vocabularyStore = useVocabularyStore()

const thing = ref<Thing>()
const datastream = ref<Datastream>(new Datastream(props.thing.id))

const timeUnits = ['seconds', 'minutes', 'hours', 'days']

const openUnitForm = ref(false)
const isEdit = ref(!!props.datastream?.id)
const showTemplateModal = ref(false)
const showSensorModal = ref(false)
const showPLModal = ref(false)
const showOPModal = ref(false)
const showLinkedMetadataHelp = ref(false)

const valid = ref(false)
const myForm = ref<VForm>()
const selectedDatastreamID = ref('')
const intendedTimeSpacingRef = ref<VForm>()

const { hasPermission } = useWorkspacePermissions()

const {
  sensors,
  units,
  observedProperties,
  processingLevels,
  formattedObservedProperties,
  formattedProcessingLevels,
  fetchMetadata,
} = useMetadata(toRef(props, 'workspace'))

const handleMetadataUploaded = async (dsKey: string, newId: string) => {
  await fetchMetadata(props.workspace.id)
  ;(datastream.value as any)[dsKey] = newId
}

const originalName = ref('')
const originalDescription = ref('')

const generateDefaultName = () => {
  const OP = observedProperties.value.find(
    (pl) => pl.id === datastream.value.observedPropertyId
  )?.name
  const PL = processingLevels.value.find(
    (pl) => pl.id === datastream.value.processingLevelId
  )?.code
  return `${OP} at ${thing.value?.samplingFeatureCode} with processing level ${PL}`
}

const generateDefaultDescription = () => {
  const OP = observedProperties.value.find(
    (pl) => pl.id === datastream.value.observedPropertyId
  )?.name
  const PL = processingLevels.value.find(
    (pl) => pl.id === datastream.value.processingLevelId
  )?.code
  const sensorName = sensors.value.find(
    (pl) => pl.id === datastream.value.sensorId
  )?.name
  const unitName = units.value.find(
    (pl) => pl.id === datastream.value.unitId
  )?.name
  return `A datastream of ${OP} at ${thing.value?.name} with processing level ${PL} and sampled medium ${datastream.value.sampledMedium} created using a method with name ${sensorName} having units of ${unitName}`
}

watch(selectedDatastreamID, async () => {
  try {
    const fetchedDS = await hs.datastreams.getItem(selectedDatastreamID.value)
    if (!fetchedDS) return
    Object.assign(datastream.value, {
      ...datastream.value,
      sensorId: fetchedDS.sensorId,
      observedPropertyId: fetchedDS.observedPropertyId,
      processingLevelId: fetchedDS.processingLevelId,
      unitId: fetchedDS.unitId,
      timeAggregationIntervalUnit: fetchedDS.timeAggregationIntervalUnit,
      intendedTimeSpacingUnit: fetchedDS.intendedTimeSpacingUnit,
      name: fetchedDS.name,
      description: fetchedDS.description,
      sampledMedium: fetchedDS.sampledMedium,
      noDataValue: fetchedDS.noDataValue,
      aggregationStatistic: fetchedDS.aggregationStatistic,
      status: fetchedDS.status,
      timeAggregationInterval: fetchedDS.timeAggregationInterval,
      intendedTimeSpacing: fetchedDS.intendedTimeSpacing,
    })
  } catch (error) {
    console.error('Error loading datastream template', error)
  }
  await myForm.value?.validate()
})

function onSpacingUnitChange() {
  intendedTimeSpacingRef.value?.validate()
}

async function onSubmit() {
  await myForm.value?.validate()
  if (!valid.value) return
  datastream.value.thingId = props.thing.id
  if (isEdit.value) {
    try {
      await hs.datastreams.update(datastream.value)
      emit('updated', datastream.value)
    } catch (error) {
      console.error('Error updating datastream', error)
    }
  } else {
    try {
      await hs.datastreams.create(datastream.value)
      emit('created')
    } catch (error) {
      console.error('Error creating datastream', error)
    }
  }
  emit('close')
}

onMounted(async () => {
  try {
    if (isEdit.value) {
      datastream.value = props.datastream!
      originalName.value = datastream.value.name
      originalDescription.value = datastream.value.description
    }
    thing.value = props.thing
  } catch (error) {
    Snackbar.error('Unable to fetch data from the API.')
    console.error('Error fetching datastream data from DB.', error)
  }
})
</script>
