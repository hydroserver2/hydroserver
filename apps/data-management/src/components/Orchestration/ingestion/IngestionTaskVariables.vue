<template>
  <div class="task-form-section">
    <div class="task-form-section-header task-form-section-header-stack">
      <h3 class="task-form-section-title">Template variables</h3>
      <p class="task-form-section-copy">
        Fill in values for URL placeholders defined in this data connection.
      </p>
    </div>

    <div class="task-form-template-grid">
      <div
        v-for="variable in placeholders"
        :key="variable.name"
        class="task-form-field"
      >
        <label class="task-form-label" :for="`task-variable-${variable.name}`">
          {{ variable.name }} <span class="task-form-required">*</span>
        </label>
        <v-text-field
          :id="`task-variable-${variable.name}`"
          v-model="task.taskVariables[variable.name]"
          :placeholder="templateVariablePlaceholder(variable.name)"
          :rules="rules.requiredAndMaxLength255"
          variant="outlined"
          rounded="lg"
          density="compact"
          hide-details="auto"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Task } from '@hydroserver/client'
import { rules } from '@/utils/rules'

type Placeholder = {
  name: string
}

const task = defineModel<Task>('task', { required: true })

defineProps<{
  placeholders: Placeholder[]
}>()

function templateVariablePlaceholder(name: string) {
  return `e.g. ${name.toUpperCase()}`
}
</script>

<style scoped>
.task-form-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.task-form-section-header {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.task-form-section-header-stack {
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
}
.task-form-section-title {
  font-size: 0.67rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 800;
  color: #4f4b59;
}
.task-form-section-copy {
  color: #5f5a67;
  font-size: 0.72rem;
  line-height: 1.3;
}
.task-form-template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 420px));
  gap: 8px;
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
