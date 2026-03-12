<template>
  <v-card v-if="hasWorkspaces">
    <v-toolbar
      :color="toolbarColor"
      :title="useWorkspaceVariables ? 'Workspace metadata' : 'System metadata'"
    >
      <v-spacer />

      <template v-slot:extension>
        <v-tabs
          v-model="tab"
          color="secondary-lighten-5"
          scrollable
          class="my-2"
        >
          <v-tab v-for="item in metaMap">{{ item.name }}</v-tab>
        </v-tabs>
      </template>

      <v-btn-add
        v-if="hasCRUDPermissions"
        :prependIcon="mdiPlus"
        color="white"
        class="mx-2"
        @click="metaMap[tab]?.openDialog()"
        >Add new {{ metaMap[tab]?.singularName }}</v-btn-add
      >
    </v-toolbar>

    <v-toolbar :color="toolbarColor" height="5"></v-toolbar>

    <v-window v-model="tab" class="elevation-3" v-if="selectedWorkspace">
      <v-window-item :value="0">
        <SensorTable
          :key="sensorKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
        />
      </v-window-item>

      <v-window-item :value="1">
        <ObservedPropertyTable
          :key="OPKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
        />
      </v-window-item>

      <v-window-item :value="2">
        <ProcessingLevelTable
          :key="PLKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
        />
      </v-window-item>

      <v-window-item :value="3">
        <UnitTable
          :key="unitKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
        />
      </v-window-item>

      <v-window-item :value="4">
        <ResultQualifierTable
          :key="qualifierKey"
          :search="search"
          :workspace-id="workspaceId"
          :can-edit="hasCRUDPermissions"
        />
      </v-window-item>
    </v-window>
  </v-card>

  <v-dialog v-model="openSensorCreate" width="60rem">
    <SensorFormCard
      @close="openSensorCreate = false"
      @created="refreshSensorTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>

  <v-dialog v-model="openOPCreate" width="60rem">
    <ObservedPropertyFormCard
      @close="openOPCreate = false"
      @created="refreshOPTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>

  <v-dialog v-model="openPLCreate" width="60rem">
    <ProcessingLevelFormCard
      @close="openPLCreate = false"
      @created="refreshPLTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>

  <v-dialog v-model="openUnitCreate" width="60rem">
    <UnitFormCard
      @close="openUnitCreate = false"
      @created="refreshUnitTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>

  <v-dialog v-model="openRQCreate" width="60rem">
    <ResultQualifierFormCard
      @close="openRQCreate = false"
      @created="refreshRQTable"
      :workspace-id="workspaceId"
    />
  </v-dialog>
</template>

<script lang="ts" setup>
import UnitTable from '@/components/Metadata/UnitTable.vue'
import SensorTable from '@/components/Metadata/SensorTable.vue'
import ResultQualifierTable from '@/components/Metadata/ResultQualifierTable.vue'
import ProcessingLevelTable from '@/components/Metadata/ProcessingLevelTable.vue'
import ObservedPropertyTable from '@/components/Metadata/ObservedPropertyTable.vue'
import UnitFormCard from '@/components/Metadata/UnitFormCard.vue'
import SensorFormCard from '@/components/Metadata/SensorFormCard.vue'
import ResultQualifierFormCard from '@/components/Metadata/ResultQualifierFormCard.vue'
import ProcessingLevelFormCard from '@/components/Metadata/ProcessingLevelFormCard.vue'
import ObservedPropertyFormCard from '@/components/Metadata/ObservedPropertyFormCard.vue'
import { computed, ref } from 'vue'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'
import { Workspace } from '@hydroserver/client'
import { useMetadata } from '@/store/metadata'
import { mdiPlus } from '@mdi/js'

const { tab } = storeToRefs(useMetadata())
const { selectedWorkspace, hasWorkspaces } = storeToRefs(useWorkspaceStore())

const workspaceRef = computed<Workspace | undefined>(
  () => selectedWorkspace.value ?? undefined
)

const props = defineProps({
  toolbarColor: String,
  useWorkspaceVariables: Boolean,
  search: String,
  tab: Number,
})

const workspaceId = computed(() =>
  props.useWorkspaceVariables ? selectedWorkspace.value!.id : undefined
)

const { isAdmin } = useWorkspacePermissions(workspaceRef)

const hasCRUDPermissions = computed(
  () => !!(props.useWorkspaceVariables || isAdmin())
)
const openUnitCreate = ref(false)
const unitKey = ref(0)
const refreshUnitTable = () => (unitKey.value += 1)

const openRQCreate = ref(false)
const qualifierKey = ref(0)
const refreshRQTable = () => (qualifierKey.value += 1)

const openPLCreate = ref(false)
const PLKey = ref(0)
const refreshPLTable = () => (PLKey.value += 1)

const openOPCreate = ref(false)
const OPKey = ref(0)
const refreshOPTable = () => (OPKey.value += 1)

const openSensorCreate = ref(false)
const sensorKey = ref(0)
const refreshSensorTable = () => (sensorKey.value += 1)

const metaMap: Record<string, any> = {
  0: {
    name: 'Sensors',
    openDialog: () => (openSensorCreate.value = true),
    singularName: 'sensor',
  },
  1: {
    name: 'Observed properties',
    openDialog: () => (openOPCreate.value = true),
    singularName: 'observed property',
  },
  2: {
    name: 'Processing levels',
    openDialog: () => (openPLCreate.value = true),
    singularName: 'processing level',
  },
  3: {
    name: 'Units',
    openDialog: () => (openUnitCreate.value = true),
    singularName: 'unit',
  },
  4: {
    name: 'Result qualifiers',
    openDialog: () => (openRQCreate.value = true),
    singularName: 'result qualifier',
  },
}
</script>
