<template>
  <v-input
    v-bind="$attrs"
    :model-value="modelValue"
    :rules="rules"
    :disabled="disabled"
    :hide-details="hideDetails"
    class="datastream-card-selector"
    :class="`datastream-card-selector--${density}`"
  >
    <template #default="{ isValid }">
      <div class="datastream-card-selector__body">
        <p v-if="hint" class="datastream-card-selector__hint hs-text-sm">
          {{ hint }}
        </p>

        <div class="datastream-card-selector__control">
          <v-btn
            variant="outlined"
            type="button"
            :disabled="disabled"
            :loading="loading"
            :aria-label="buttonAriaLabel"
            class="datastream-card-selector__button"
            :class="{
              'datastream-card-selector__button--empty': !selectedDatastream,
              'datastream-card-selector__button--invalid':
                isValid.value === false,
            }"
            @click="openSelector"
          >
            <span
              v-if="!selectedDatastream"
              class="datastream-card-selector__prompt"
            >
              <v-icon :icon="mdiPlusCircleOutline" size="18" />
              <span>{{ promptText }}</span>
            </span>
            <span v-else class="datastream-card-selector__selection">
              <span class="datastream-card-selector__name">{{
                selectedDatastreamName
              }}</span>
              <template v-if="selectedMonitoringSiteName">
                <span
                  class="datastream-card-selector__separator"
                  aria-hidden="true"
                  >@</span
                >
                <span class="datastream-card-selector__site">{{
                  selectedMonitoringSiteName
                }}</span>
              </template>
            </span>
          </v-btn>

          <v-btn-icon
            v-if="clearable && modelValue && !disabled"
            :icon="mdiClose"
            size="small"
            :aria-label="`Clear ${labelText.toLocaleLowerCase()}`"
            @click.stop="emit('update:modelValue', null)"
          />
        </div>
      </div>
    </template>
  </v-input>

  <v-dialog v-model="selectorOpen" width="75rem">
    <DatastreamSelectorCard
      :card-title="`Select ${labelText.toLocaleLowerCase()}`"
      :datastreams="datastreams"
      :monitoring-sites="monitoringSites"
      :workspace-id="workspaceId"
      :monitoring-site-id="monitoringSiteId"
      :scope-note="scopeNote"
      :draft-datastreams="draftDatastreams"
      :enforce-unique-selections="enforceUniqueSelections"
      :selected-datastream-id="modelValue"
      @selected-datastream="selectDatastream"
      @close="selectorOpen = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type {
  Datastream,
  DatastreamExtended,
  MonitoringSite,
} from '@hydroserver/client'
import { mdiClose, mdiPlusCircleOutline } from '@mdi/js'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'
import DatastreamSelectorCard from '@/components/Datastream/DatastreamSelectorCard.vue'

type Rule = (value: any) => true | string
type Density = 'default' | 'comfortable' | 'compact'

const props = withDefaults(
  defineProps<{
    modelValue: string | null
    datastreams: Datastream[]
    label: string
    workspaceId?: string | null
    monitoringSites?: MonitoringSite[]
    monitoringSiteId?: string | null
    draftDatastreams?: DatastreamExtended[]
    enforceUniqueSelections?: boolean
    // Static helper text between the label and the control, so it reads as
    // belonging to this field rather than to the one below it.
    hint?: string | null
    // Explanation shown inside the selector dialog, where a scoped list is
    // what surprises people. Safe to interpolate loaded data into.
    scopeNote?: string | null
    placeholder?: string | null
    loading?: boolean
    disabled?: boolean
    rules?: Rule[]
    density?: Density
    clearable?: boolean
    hideDetails?: boolean | 'auto'
  }>(),
  {
    workspaceId: null,
    monitoringSites: undefined,
    monitoringSiteId: null,
    draftDatastreams: undefined,
    enforceUniqueSelections: false,
    hint: null,
    scopeNote: null,
    placeholder: null,
    loading: false,
    disabled: false,
    rules: () => [],
    density: 'default',
    clearable: true,
    hideDetails: 'auto',
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: string | null): void
  // The resolved record, for callers that need more than the id.
  (e: 'select', datastream: DatastreamExtended): void
}>()

// The template has two roots (the input and its dialog), so fallthrough attrs
// would otherwise be dropped — callers pass spacing classes here.
defineOptions({ inheritAttrs: false })
const selectorOpen = ref(false)

// The label is not rendered as a caption — the button says what it selects,
// and the hint above it carries the scope. It names the field for the dialog
// title and for screen readers. Strip a trailing asterisk from older callers.
const labelText = computed(() => props.label.replace(/\s*\*$/, ''))
const promptText = computed(
  () => props.placeholder ?? `Select ${labelText.value.toLocaleLowerCase()}`
)

const buttonAriaLabel = computed(() =>
  props.modelValue
    ? `${labelText.value}: ${selectedDatastreamName.value}`
    : promptText.value
)

const selectedDatastream = computed(() =>
  props.datastreams.find((datastream) => datastream.id === props.modelValue)
)
const showMonitoringSiteContext = computed(
  () =>
    !props.monitoringSiteId &&
    new Set(props.datastreams.map(datastreamMonitoringSiteId).filter(Boolean))
      .size > 1
)
const selectedDatastreamName = computed(
  () => selectedDatastream.value?.name || 'Unnamed datastream'
)
const selectedMonitoringSiteName = computed(() => {
  if (!showMonitoringSiteContext.value) return null
  const datastream = selectedDatastream.value as
    (Datastream & Record<string, any>) | undefined
  return datastream?.monitoringSite?.name ?? null
})

function openSelector() {
  if (!props.disabled) selectorOpen.value = true
}
function selectDatastream(datastream: DatastreamExtended) {
  emit('update:modelValue', datastream.id)
  emit('select', datastream)
  selectorOpen.value = false
}
</script>

<style scoped>
.datastream-card-selector :deep(.v-input__control) {
  display: block;
}
.datastream-card-selector__hint {
  margin: 0 0 var(--hs-space-6);
  color: var(--hs-text-secondary);
}
.datastream-card-selector__control {
  display: flex;
  gap: var(--hs-space-4);
  align-items: center;
}

/* Doubled class beats Vuetify's own `.v-btn--variant-outlined` border. */
.datastream-card-selector .datastream-card-selector__button {
  flex: 1;
  min-width: 0;
  height: auto;
  padding-block: var(--hs-space-12);
  padding-inline: var(--hs-space-12);
  color: var(--hs-text-primary);
  letter-spacing: normal;
  text-transform: none;
  background: var(--hs-surface);
  border: 2px solid rgb(var(--v-theme-primary));
  border-radius: var(--hs-radius-lg);
}
.datastream-card-selector--compact .datastream-card-selector__button {
  padding-block: var(--hs-space-8);
}
.datastream-card-selector .datastream-card-selector__button--empty {
  color: rgb(var(--v-theme-primary));
  background: var(--hs-surface-muted);
  border-style: dashed;
}
.datastream-card-selector .datastream-card-selector__button--invalid {
  color: var(--hs-error);
  border-color: var(--hs-error);
}
.datastream-card-selector__button :deep(.v-btn__content) {
  width: 100%;
  min-width: 0;
  justify-content: flex-start;
  overflow: visible;
  text-align: left;
  white-space: normal;
}
.datastream-card-selector__prompt {
  display: inline-flex;
  gap: var(--hs-space-6);
  align-items: center;
  font-weight: var(--hs-font-weight-bold);
}
.datastream-card-selector__selection {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-4);
  align-items: baseline;
  min-width: 0;
}
.datastream-card-selector__name {
  font-weight: var(--hs-font-weight-semibold);
}
.datastream-card-selector__separator,
.datastream-card-selector__site {
  color: var(--hs-text-secondary);
}
</style>
