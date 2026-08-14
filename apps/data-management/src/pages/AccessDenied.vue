<template>
  <v-container
    class="d-flex flex-column justify-center align-center py-16 min-vh-100 text-center"
  >
    <h3 class="hs-text-lg pb-5">403 - Access Denied</h3>
    <h5 class="hs-text-md">
      You don't have permission to view this page for the requested workspace.
    </h5>
    <v-btn class="mt-6" color="primary" :to="{ name: 'Orchestration' }">
      Back to job orchestration
    </v-btn>
  </v-container>
</template>

<script setup lang="ts"></script>
