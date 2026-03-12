<template>
  <v-card class="sticky-form-card d-flex flex-column">
    <div class="sticky-header">
      <div class="sticky-header-content">
        <slot name="header" />
      </div>
      <v-divider color="black" thickness="2" />
    </div>

    <div class="scroll-body">
      <slot />
    </div>

    <div class="sticky-actions">
      <v-divider color="black" thickness="2" />
      <v-card-actions>
        <slot name="actions" />
      </v-card-actions>
    </div>
  </v-card>
</template>

<style scoped>
.sticky-form-card {
  max-height: 90vh;
  height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sticky-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: white;
}

.sticky-header-content {
  padding-top: 10px;
  padding-bottom: 10px;
}

.scroll-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

.sticky-actions {
  position: sticky;
  bottom: 0;
  z-index: 3;
  background: white;
}
</style>
