import { defineStore } from 'pinia'
import { User } from '@hydroserver/client'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const user = ref<User>(new User())

  return {
    user,
  }
})
