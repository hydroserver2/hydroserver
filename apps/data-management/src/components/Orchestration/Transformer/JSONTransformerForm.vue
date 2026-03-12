<template>
  <v-row v-if="transformer.type === 'JSON'">
    <v-col cols="12">
      <v-card-item>
        <v-card-title>JMESPath</v-card-title>
      </v-card-item>
      <v-card-text>
        <v-text-field
          v-model="transformer.settings.JMESPath"
          label="JMESPath *"
          density="compact"
          rounded="lg"
          :prepend-inner-icon="mdiFileTree"
          :rules="rules.required"
        />
      </v-card-text>
    </v-col>
  </v-row>
  <v-row class="mt-0">
    <v-col md="6">
      <TimestampFields />
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { useDataConnectionStore } from '@/store/dataConnection'
import { storeToRefs } from 'pinia'
import TimestampFields from '@/components/Orchestration/Timestamp/TimestampFields.vue'
import { rules } from '@/utils/rules'
import { mdiFileTree } from '@mdi/js'

const { transformer } = storeToRefs(useDataConnectionStore())
</script>
