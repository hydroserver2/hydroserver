import { defineStore } from 'pinia'
import { ref } from 'vue'
import { Task } from '@hydroserver/client'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])

  return {
    tasks,
  }
})
