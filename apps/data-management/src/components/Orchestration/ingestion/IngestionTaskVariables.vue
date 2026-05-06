<template>
  <div class="flex flex-col gap-1.5">
    <div class="flex flex-col gap-px">
      <h3 class="text-[0.67rem] tracking-[0.08em] uppercase font-extrabold text-[#4f4b59]">
        Template variables
      </h3>
      <p class="text-[#5f5a67] text-[0.72rem] leading-[1.3]">
        Fill in values for URL placeholders defined in this data connection.
      </p>
    </div>

    <div class="grid grid-cols-[repeat(auto-fit,minmax(260px,420px))] gap-2">
      <div
        v-for="variable in placeholders"
        :key="variable.name"
        class="flex flex-col gap-1"
      >
        <label
          class="text-[0.74rem] font-bold text-[#1f1d24]"
          :for="`task-variable-${variable.name}`"
        >
          {{ variable.name }} <span class="text-[#d32f2f]">*</span>
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
