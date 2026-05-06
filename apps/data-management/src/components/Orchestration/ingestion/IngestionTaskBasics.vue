<template>
  <div class="flex flex-col gap-1.5">
    <div class="flex flex-col gap-1">
      <label class="text-[0.74rem] font-bold text-[#1f1d24]" for="task-name">
        Task name <span class="text-[#d32f2f]">*</span>
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
