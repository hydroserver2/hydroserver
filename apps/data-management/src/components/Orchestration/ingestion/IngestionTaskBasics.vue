<template>
  <div class="task-form-section">
    <div class="task-form-field">
      <label class="task-form-label" for="task-name">
        Task name <span class="task-form-required">*</span>
      </label>
      <v-text-field
        id="task-name"
        v-model="task.name"
        placeholder="e.g. North Fork telemetry import"
        :rules="rules.requiredAndMaxLength255"
        variant="outlined"
        rounded="lg"
        density="compact"
        hide-details="auto"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Task } from '@hydroserver/client'
import { rules } from '@/utils/rules'

const task = defineModel<Task>('task', { required: true })
</script>

<style scoped>
.task-form-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.task-form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.task-form-label {
  font-size: 0.74rem;
  font-weight: 700;
  color: #1f1d24;
}
.task-form-required {
  color: #d32f2f;
}
</style>
