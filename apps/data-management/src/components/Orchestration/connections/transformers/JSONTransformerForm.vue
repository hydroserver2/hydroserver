<template>
  <v-row>
    <v-col cols="12" md="6">
      <v-card-item>
        <v-card-title>JMESPath</v-card-title>
      </v-card-item>
      <v-card-text>
        <v-text-field
          v-model="jsonPayload.jmespath"
          label="JMESPath expression"
          density="compact"
          rounded="lg"
          :prepend-inner-icon="mdiFileTree"
          clearable
        />
      </v-card-text>
    </v-col>
    <v-col cols="12" md="6">
      <TimestampFields />
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDataConnectionStore } from '@/store/dataConnection'
import { storeToRefs } from 'pinia'
import TimestampFields from '@/components/Orchestration/connections/timestamps/TimestampFields.vue'
import type { JSONPayload } from '@hydroserver/client'
import { mdiFileTree } from '@mdi/js'

const { dataConnection } = storeToRefs(useDataConnectionStore())
const jsonPayload = computed(() => dataConnection.value.payload as JSONPayload)
</script>
