import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSidebarStore = defineStore('sidebar', () => {
  const isOpen = ref(false)
  const isExplicit = ref(false)

  function setOpen(value: boolean, explicit = false) {
    isOpen.value = value
    if (explicit) isExplicit.value = true
  }

  function toggle() {
    isOpen.value = !isOpen.value
    isExplicit.value = true
  }

  return { isOpen, isExplicit, setOpen, toggle }
})
