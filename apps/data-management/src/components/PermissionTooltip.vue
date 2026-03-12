<script setup lang="ts">
const props = defineProps<{
  hasPermission: boolean
  message?: string
}>()
</script>

<template>
  <!-- Has permission: render the live version -->
  <template v-if="props.hasPermission">
    <slot />
  </template>

  <!-- No permission: render disabled version with tooltip -->
  <v-tooltip v-else location="bottom" content-class="pa-0 ma-0 bg-transparent">
    <template #activator="{ props: activatorProps }">
      <span v-bind="activatorProps" class="d-inline-block">
        <slot name="denied" />
      </span>
    </template>

    <v-card
      elevation="2"
      class="ma-0 pa-0"
      style="max-width: 480px; min-width: 300px"
    >
      <v-card-text class="px-4 py-2">
        <v-row>
          <v-col>
            {{
              props.message ??
              "You don't have permissions to perform this action. Contact your system administrator to change your permissions."
            }}
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-tooltip>
</template>
